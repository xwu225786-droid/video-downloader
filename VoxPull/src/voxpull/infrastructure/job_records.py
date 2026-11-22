"""Local durable task records, with one writer per data directory."""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from pathlib import Path

from voxpull.infrastructure.file_lock import lock_file, unlock_file

from voxpull.application.job_service import InMemoryJobRepository, JobService
from voxpull.domain.models import (
    Job, JobBatch, JobErrorInfo, JobResult, JobStage, JobStatus, MediaAssetInfo,
    MediaAssetKind, MediaInfo, MediaKind, Transcript, TranscriptSegment,
)
from voxpull.infrastructure.cookies import save_storage_state


def _encode(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def _decode_job(data):
    data["status"] = JobStatus(data["status"])
    data["stage"] = JobStage(data["stage"])
    data["created_at"] = datetime.fromisoformat(data["created_at"])
    if data.get("error"):
        data["error"] = JobErrorInfo(**data["error"])
    if data.get("result"):
        result = data["result"]
        media = result["media"]
        media["kind"] = MediaKind(media["kind"])
        media["assets"] = tuple(MediaAssetInfo(**{**asset, "kind": MediaAssetKind(asset["kind"])})
                                for asset in media.get("assets", []))
        transcript = result.get("transcript")
        if transcript:
            transcript["segments"] = tuple(TranscriptSegment(**segment) for segment in transcript["segments"])
            transcript = Transcript(**transcript)
        data["result"] = JobResult(MediaInfo(**media), transcript)
    return Job(**data)


class FileJobRepository(InMemoryJobRepository):
    def __init__(self, root: Path):
        super().__init__()
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def load(self):
        with self._lock:
            for path in self.root.glob("job-*.json"):
                job = _decode_job(json.loads(path.read_text(encoding="utf-8")))
                if job.metadata.get("summary_state") == "generating":
                    job.metadata["summary_state"] = "failed"
                    self._save(job)
                if job.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
                    job.status, job.stage = JobStatus.FAILED, JobStage.FAILED
                    job.message = "上次处理已中断，可单独重试"
                    job.error = JobErrorInfo("service_stopped", job.message, True)
                    self._save(job)
                self._jobs[job.id] = job

    def _save(self, job):
        data = json.loads(json.dumps(asdict(job), default=_encode))
        save_storage_state(self.root / f"job-{job.id}.json", data)

    def add(self, job):
        with self._lock:
            if job.id in self._jobs:
                raise ValueError(f"Duplicate job: {job.id}")
            self._save(job)
            super().add(job)

    def update(self, job_id, **changes):
        with self._lock:
            job = super().update(job_id, **changes)
            self._save(job)
            return job


class FileJobService(JobService):
    async def start(self):
        if self._worker_tasks:
            return
        self._record_lock = (self.repository.root / ".writer.lock").open("a")
        for attempt in range(100):
            try:
                lock_file(self._record_lock, blocking=False)
                break
            except BlockingIOError:
                if attempt == 99:
                    self._record_lock.close()
                    raise RuntimeError("另一个任务后台仍在使用记录目录")
                await asyncio.sleep(.1)
        self.repository.load()
        path = self.repository.root / "batches.json"
        if path.exists():
            self._batches = {key: JobBatch(**{**value, "job_ids": tuple(value["job_ids"])})
                             for key, value in json.loads(path.read_text(encoding="utf-8")).items()}
        await super().start()

    def _save_batches(self):
        save_storage_state(self.repository.root / "batches.json",
                           {key: asdict(value) for key, value in self._batches.items()})

    def submit_batch(self, *args, **kwargs):
        batch = super().submit_batch(*args, **kwargs)
        self._save_batches()
        return batch

    def retry_batch(self, *args, **kwargs):
        batch = super().retry_batch(*args, **kwargs)
        self._save_batches()
        return batch

    async def stop(self):
        try:
            await super().stop()
        finally:
            lock = getattr(self, "_record_lock", None)
            if lock and not lock.closed:
                unlock_file(lock)
                lock.close()
