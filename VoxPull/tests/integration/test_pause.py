import asyncio
import sys
import threading
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from voxpull.app import create_app
from voxpull.api.schemas import batch_to_response
from voxpull.application.job_service import InMemoryJobRepository, JobService
from voxpull.application.pipeline import TranscriptionPipeline
from voxpull.domain.models import JobStage, JobStatus
from voxpull.infrastructure.downloader import YtDlpDownloader, _check_download_cancelled
from voxpull.infrastructure.job_records import FileJobRepository
from voxpull.infrastructure.processes import ProcessRunner
from voxpull.infrastructure.storage import LocalStorage
from test_api import completed_video_job, make_settings
from test_pipeline import FakeBrowser, FakeDownloader, FakeAudioExtractor, FakeTranscriber


async def until(predicate):
    async with asyncio.timeout(2):
        while not predicate():
            await asyncio.sleep(.005)


async def test_pause_api_stops_only_selected_job_and_survives_reload(tmp_path):
    app = create_app(make_settings(tmp_path))
    service = app.state.container.job_service
    service.max_concurrency = 1
    started, stopped = asyncio.Event(), asyncio.Event()
    executions = []

    class Pipeline:
        async def execute(self, job_id):
            executions.append(job_id)
            service.repository.update(job_id, status=JobStatus.RUNNING)
            if len(executions) == 1:
                started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    stopped.set()
            else:
                service.repository.update(job_id, status=JobStatus.COMPLETED, stage=JobStage.COMPLETED)

    service.pipeline = Pipeline()
    async with app.router.lifespan_context(app):
        done = completed_video_job()
        service.repository.add(done)
        one = service.submit("https://example.test/one", "auto", False, False)
        await started.wait()
        queued = service.submit("https://example.test/queued", "zh")
        next_job = service.submit("https://example.test/next", "zh")
        async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
            assert (await client.post(f"/api/jobs/{one.id}/pause", headers={"Origin": "https://foreign.test"})).status_code == 403
            assert service.get(one.id).status is JobStatus.RUNNING
            assert (await client.post(f"/api/jobs/{queued.id}/pause")).json()["status"] == "paused"
            response = await client.post(f"/api/jobs/{one.id}/pause")
            assert response.status_code == 200 and response.json()["status"] == "paused"
            assert stopped.is_set()
            await asyncio.wait_for(service.queue.join(), 2)
            assert executions == [one.id, next_job.id]
            assert service.get(next_job.id).status is JobStatus.COMPLETED
            assert service.get(done.id) == done
            assert (await client.post(f"/api/jobs/{one.id}/pause")).json()["status"] == "paused"
            assert (await client.post(f"/api/jobs/{done.id}/pause")).status_code == 409
            assert (await client.post("/api/jobs/missing/pause")).status_code == 404
            retry = await client.post(f"/api/jobs/{one.id}/retry")
            assert retry.status_code == 202
            await asyncio.wait_for(service.queue.join(), 2)
            retried = service.get(retry.json()["job_id"])
            assert (retried.content, retried.language, retried.save_video, retried.extract_txt) == (one.content, "auto", False, False)
            assert service.get(one.id).status is JobStatus.PAUSED
            assert not service.has_active_jobs()
    restored = FileJobRepository(service.repository.root)
    restored.load()
    assert restored.get(one.id).status is JobStatus.PAUSED
    assert restored.get(queued.id).status is JobStatus.PAUSED


@pytest.mark.parametrize("phase", ["browser", "download", "audio", "transcribe"])
async def test_pause_cleans_current_workspace_and_preserves_saved_files(tmp_path, phase):
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def hold():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    class Browser(FakeBrowser):
        async def acquire(self, *args, **kwargs):
            if phase == "browser":
                await hold()
            return await super().acquire(*args, **kwargs)

    class Downloader(FakeDownloader):
        async def download(self, *args, **kwargs):
            if phase == "download":
                await hold()
            return await super().download(*args, **kwargs)

    class Audio(FakeAudioExtractor):
        async def extract(self, *args):
            if phase == "audio":
                await hold()
            return await super().extract(*args)

    class Transcriber(FakeTranscriber):
        async def transcribe(self, *args):
            if phase == "transcribe":
                await hold()
            return await super().transcribe(*args)

    repository = InMemoryJobRepository()
    storage = LocalStorage(tmp_path / "work", tmp_path / "videos")
    unrelated = storage.videos_root / "original.mp4"
    unrelated.write_bytes(b"keep original")
    pipeline = TranscriptionPipeline(repository, Browser(), Downloader(), Audio(), Transcriber(), storage)
    service = JobService(repository, pipeline, 10, max_concurrency=1)
    await service.start()
    try:
        job = service.submit("https://www.douyin.com/video/123", "zh", True)
        await asyncio.wait_for(started.wait(), 2)
        before = repository.get(job.id)
        saved = {str(p): p.read_bytes() for p in storage.videos_root.rglob("*") if p.is_file()}
        paused = await service.pause_job(job.id)
        assert paused.status is JobStatus.PAUSED and paused.progress == before.progress
        assert cancelled.is_set() and not (tmp_path / "work" / job.id).exists()
        assert all(Path(p).read_bytes() == value for p, value in saved.items())
        assert unrelated.read_bytes() == b"keep original"
        pipeline._scaled_progress(job.id, 100, 0, 100, "late callback")
        assert repository.get(job.id) == paused
        await asyncio.wait_for(service.queue.join(), 2)
    finally:
        await service.stop()


async def test_paused_batch_item_never_executes_and_can_retry(tmp_path):
    repo = InMemoryJobRepository()
    release = asyncio.Event()
    started = []

    class Pipeline:
        async def execute(self, job_id):
            started.append(job_id)
            repo.update(job_id, status=JobStatus.RUNNING)
            await release.wait()
            repo.update(job_id, status=JobStatus.COMPLETED, stage=JobStage.COMPLETED, progress=100)

    service = JobService(repo, Pipeline(), max_queue=1, max_concurrency=1)
    await service.start()
    try:
        batch = service.submit_batch([f"https://example.test/{i}" for i in range(4)], "auto", False, extract_txt=False)
        await until(lambda: len(started) == 1)
        await service.pause_job(batch.job_ids[-1])
        release.set()
        await until(lambda: not service.has_active_jobs())
        assert batch.job_ids[-1] not in started
        response = batch_to_response(batch, service.batch_jobs(batch))
        assert response.paused == 1 and response.status == "paused" and response.running == response.queued == 0
        retry = service.retry_batch(batch.id)
        assert retry.job_ids[:-1] == batch.job_ids[:-1]
        await until(lambda: not service.has_active_jobs())
        assert all(job.status is JobStatus.COMPLETED for job in service.batch_jobs(retry))
        assert repo.get(batch.job_ids[-1]).status is JobStatus.PAUSED
    finally:
        release.set()
        await service.stop()


async def test_pausing_thread_download_joins_writer_before_workspace_cleanup(tmp_path, monkeypatch):
    downloader = YtDlpDownloader(5)
    started, stopped = threading.Event(), threading.Event()
    release = threading.Event()

    def download(*_):
        started.set()
        try:
            release.wait(2)
            _check_download_cancelled()
            (tmp_path / "orphan.mp4").write_bytes(b"must not be written")
        finally:
            stopped.set()

    monkeypatch.setattr(downloader, "_download_sync", download)
    from voxpull.domain.models import MediaMetadata
    task = asyncio.create_task(downloader.download("https://example.test", MediaMetadata("x", "x"), tmp_path / "cookies", "test", tmp_path, lambda *_: None))
    try:
        await until(started.is_set)
        task.cancel()
        await asyncio.sleep(.01)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert stopped.is_set() and not (tmp_path / "orphan.mp4").exists()
    finally:
        release.set()


async def test_cancelling_process_terminates_only_its_process_group(tmp_path):
    runner = ProcessRunner()
    first = asyncio.create_task(runner.run([sys.executable, "-c", "import time; time.sleep(30)"], timeout=40))
    second = asyncio.create_task(runner.run([sys.executable, "-c", "import time; time.sleep(0.2); print('ok')"], timeout=3))
    try:
        await until(lambda: len(runner._active) == 2)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert (await second).stdout.strip() == "ok"
        assert not runner._active
    finally:
        await runner.close()
