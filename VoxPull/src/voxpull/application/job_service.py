from __future__ import annotations

import asyncio
import copy
import logging
import threading
import uuid
from dataclasses import replace

from voxpull.domain.errors import InvalidInputError, QueueFullError
from voxpull.domain.models import Job, JobBatch, JobErrorInfo, JobStage, JobStatus
from voxpull.domain.ports import JobRepositoryPort


_STATUS_TRANSITIONS = {
    JobStatus.QUEUED: {JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.FAILED, JobStatus.PAUSED},
    JobStatus.RUNNING: {JobStatus.RUNNING, JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PAUSED},
    JobStatus.COMPLETED: {JobStatus.COMPLETED},
    JobStatus.FAILED: {JobStatus.FAILED},
    JobStatus.PAUSED: {JobStatus.PAUSED},
}

_STAGE_ORDER = {
    JobStage.QUEUED: 0,
    JobStage.ACQUIRING_COOKIE: 1,
    JobStage.DOWNLOADING: 2,
    JobStage.EXTRACTING_AUDIO: 3,
    JobStage.TRANSCRIBING: 4,
    JobStage.COMPLETED: 5,
    JobStage.FAILED: 5,
    JobStage.PAUSED: 5,
}


logger = logging.getLogger(__name__)


class InMemoryJobRepository(JobRepositoryPort):
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.RLock()

    def add(self, job: Job) -> None:
        with self._lock:
            if job.id in self._jobs:
                raise ValueError(f"Duplicate job: {job.id}")
            self._jobs[job.id] = copy.deepcopy(job)

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return copy.deepcopy(job) if job else None

    def update(self, job_id: str, **changes: object) -> Job:
        with self._lock:
            job = self._jobs[job_id]
            next_status = changes.get("status", job.status)
            if (
                isinstance(next_status, JobStatus)
                and next_status not in _STATUS_TRANSITIONS[job.status]
            ):
                raise ValueError(f"Illegal status transition: {job.status} -> {next_status}")
            next_stage = changes.get("stage", job.stage)
            if (
                isinstance(next_stage, JobStage)
                and next_stage is not JobStage.FAILED
                and _STAGE_ORDER[next_stage] < _STAGE_ORDER[job.stage]
            ):
                raise ValueError(f"Illegal stage transition: {job.stage} -> {next_stage}")
            for key, value in changes.items():
                if not hasattr(job, key):
                    raise AttributeError(key)
                setattr(job, key, value)
            return copy.deepcopy(job)


class JobService:
    def __init__(
        self,
        repository: JobRepositoryPort,
        pipeline: object,
        max_queue: int,
        max_concurrency: int = 5,
    ) -> None:
        self.repository = repository
        self.pipeline = pipeline
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=max_queue)
        self.max_concurrency = max(1, max_concurrency)
        self._worker_tasks: list[asyncio.Task[None]] = []
        self._accepting = False
        self._active_jobs: set[str] = set()
        self._job_tasks: dict[str, asyncio.Task[None]] = {}
        self._batches: dict[str, JobBatch] = {}
        self._batch_feeders: set[asyncio.Task[None]] = set()
        self._pending_batch_jobs: set[str] = set()

    async def start(self) -> None:
        if not self._worker_tasks:
            self._accepting = True
            self._worker_tasks = [
                asyncio.create_task(
                    self._worker(),
                    name=f"voxpull-job-worker-{index + 1}",
                )
                for index in range(self.max_concurrency)
            ]
            logger.info(
                "event=job_workers_started workers=%s queue_capacity=%s",
                self.max_concurrency,
                self.queue.maxsize,
            )

    async def stop(self) -> None:
        self._accepting = False
        feeders = tuple(self._batch_feeders)
        for feeder in feeders:
            feeder.cancel()
        await asyncio.gather(*feeders, return_exceptions=True)
        workers, self._worker_tasks = self._worker_tasks, []
        logger.info(
            "event=job_workers_stopping workers=%s active_jobs=%s queued_jobs=%s",
            len(workers),
            len(self._active_jobs),
            self.queue.qsize(),
        )
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        while not self.queue.empty():
            queued_id = self.queue.get_nowait()
            queued = self.repository.get(queued_id)
            if queued is not None and queued.status is JobStatus.QUEUED:
                self.repository.update(
                    queued_id, status=JobStatus.FAILED, stage=JobStage.FAILED,
                    message="服务已停止，可重试此项",
                    error=JobErrorInfo("service_stopped", "服务已停止，可重试此项", True),
                )
            self.queue.task_done()
        for batch in self._batches.values():
            for job_id in batch.job_ids:
                job = self.repository.get(job_id)
                if job is not None and job.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
                    self.repository.update(
                        job_id, status=JobStatus.FAILED, stage=JobStage.FAILED,
                        message="服务已停止，可重试此项",
                        error=JobErrorInfo("service_stopped", "服务已停止，可重试此项", True),
                    )
        logger.info("event=job_workers_stopped")

    def submit(self, content: str, language: str, save_video: bool = True, extract_txt: bool = True,
               *, job_id: str | None = None, metadata: dict | None = None) -> Job:
        if not self._accepting:
            raise QueueFullError("服务正在关闭，暂不接受新任务")
        if language not in {"zh", "auto"}:
            raise InvalidInputError("识别语言只支持 zh 或 auto")
        if self.queue.full():
            raise QueueFullError()
        job = Job(
            id=job_id or uuid.uuid4().hex,
            content=content,
            language=language,
            save_video=save_video,
            extract_txt=extract_txt,
            metadata=metadata or {},
        )
        self.repository.add(job)
        self.queue.put_nowait(job.id)
        logger.info(
            "job_id=%s event=queued language=%s save_video=%s queued_jobs=%s",
            job.id,
            job.language,
            job.save_video,
            self.queue.qsize(),
        )
        return job

    def get(self, job_id: str) -> Job | None:
        return self.repository.get(job_id)

    def retry_job(self, job_id: str) -> Job:
        job = self.get(job_id)
        if job is None:
            raise InvalidInputError("任务不存在")
        if job.status not in {JobStatus.FAILED, JobStatus.PAUSED}:
            raise InvalidInputError("只有失败或已暂停的任务可以重试")
        return self.submit(job.content, job.language, job.save_video, job.extract_txt)

    async def pause_job(self, job_id: str) -> Job:
        job = self.get(job_id)
        if job is None:
            raise InvalidInputError("任务不存在")
        if job.status not in {JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.PAUSED}:
            raise InvalidInputError("只有等待中或处理中的任务可以暂停")
        if job.status is not JobStatus.PAUSED:
            self.repository.update(
                job_id, status=JobStatus.PAUSED, stage=JobStage.PAUSED,
                message="已暂停，处理已中断，可点击重试重新开始",
                metadata={**job.metadata, "auth_status": ""},
            )
            logger.info("job_id=%s event=job_paused", job_id)
        task = self._job_tasks.get(job_id)
        if task is not None:
            if not task.cancelling():
                task.cancel()
            # The HTTP request may disconnect; cleanup must still finish.
            await asyncio.shield(asyncio.gather(task, return_exceptions=True))
        return self.get(job_id)

    def submit_batch(
        self, contents: list[str], language: str, save_video: bool, duplicate_count: int = 0,
        extract_txt: bool = True, *, auto_summary: bool = False,
    ) -> JobBatch:
        if not self._accepting:
            raise QueueFullError("服务正在关闭，暂不接受新任务")
        if language not in {"zh", "auto"} or not 1 <= len(contents) <= 200:
            raise InvalidInputError("每批需包含 1 到 200 个链接，识别语言只支持中文或自动判断")
        jobs = [Job(uuid.uuid4().hex, content, language, save_video, extract_txt=extract_txt,
                    metadata={"auto_summary": auto_summary}) for content in contents]
        for job in jobs:
            self.repository.add(job)
        batch = JobBatch(uuid.uuid4().hex, tuple(job.id for job in jobs), language, save_video, duplicate_count, extract_txt)
        self._batches[batch.id] = batch
        self._schedule_batch(batch.job_ids)
        return batch

    def get_batch(self, batch_id: str) -> JobBatch | None:
        return self._batches.get(batch_id)

    def batch_jobs(self, batch: JobBatch) -> list[Job]:
        return [job for job_id in batch.job_ids if (job := self.repository.get(job_id)) is not None]

    def retry_batch(self, batch_id: str) -> JobBatch:
        if not self._accepting:
            raise QueueFullError("服务正在关闭，暂不接受新任务")
        batch = self._batches[batch_id]
        jobs = self.batch_jobs(batch)
        if any(job.status in {JobStatus.QUEUED, JobStatus.RUNNING} for job in jobs):
            raise InvalidInputError("请等待当前批次结束，再重试失败项")
        replacements = {}
        for job in jobs:
            if job.status in {JobStatus.FAILED, JobStatus.PAUSED}:
                retried = Job(uuid.uuid4().hex, job.content, job.language, job.save_video, extract_txt=job.extract_txt,
                              metadata={"auto_summary": bool(job.metadata.get("auto_summary"))})
                self.repository.add(retried)
                replacements[job.id] = retried.id
        if not replacements:
            raise InvalidInputError("当前批次没有失败或暂停项")
        batch = replace(batch, job_ids=tuple(replacements.get(job_id, job_id) for job_id in batch.job_ids))
        self._batches[batch.id] = batch
        self._schedule_batch(tuple(replacements.values()))
        return batch

    def _schedule_batch(self, job_ids: tuple[str, ...]) -> None:
        self._pending_batch_jobs.update(job_ids)
        task = asyncio.create_task(self._feed_batch(job_ids))
        self._batch_feeders.add(task)
        task.add_done_callback(self._batch_feeders.discard)

    async def _feed_batch(self, job_ids: tuple[str, ...]) -> None:
        try:
            for job_id in job_ids:
                await self.queue.put(job_id)
                self._pending_batch_jobs.discard(job_id)
        finally:
            self._pending_batch_jobs.difference_update(job_ids)

    def queue_size(self) -> int:
        return self.queue.qsize()

    def has_active_jobs(self) -> bool:
        return bool(self._pending_batch_jobs or self._active_jobs) or not self.queue.empty()

    async def _worker(self) -> None:
        while True:
            job_id = await self.queue.get()
            self._active_jobs.add(job_id)
            logger.info(
                "job_id=%s event=worker_started active_jobs=%s queued_jobs=%s",
                job_id,
                len(self._active_jobs),
                self.queue.qsize(),
            )
            try:
                job = self.repository.get(job_id)
                if job is None or job.status is not JobStatus.QUEUED:
                    continue
                task = asyncio.create_task(self.pipeline.execute(job_id), name=f"voxpull-job-{job_id}")
                self._job_tasks[job_id] = task
                await task
            except asyncio.CancelledError:
                # Pausing a child task must not kill this queue worker.
                if asyncio.current_task().cancelling():
                    raise
            except Exception:
                logger.exception("Job worker failed unexpectedly for job %s", job_id)
                current = self.repository.get(job_id)
                if current is not None and current.status not in {
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                    JobStatus.PAUSED,
                }:
                    self.repository.update(
                        job_id,
                        status=JobStatus.FAILED,
                        stage=JobStage.FAILED,
                        message="发生内部错误，请查看本地日志",
                        error=JobErrorInfo(
                            code="internal_error",
                            message="发生内部错误，请查看本地日志",
                            retryable=False,
                        ),
                    )
            finally:
                self._job_tasks.pop(job_id, None)
                self._active_jobs.discard(job_id)
                self.queue.task_done()
                current = self.repository.get(job_id)
                logger.info(
                    "job_id=%s event=worker_finished status=%s active_jobs=%s queued_jobs=%s",
                    job_id,
                    current.status.value if current is not None else "missing",
                    len(self._active_jobs),
                    self.queue.qsize(),
                )
