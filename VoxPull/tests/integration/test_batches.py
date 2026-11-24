import asyncio
import io
import json
import zipfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from voxpull.app import create_app
from voxpull.application.job_service import InMemoryJobRepository, JobService
from voxpull.application.pipeline import extract_batch_urls
from voxpull.config import Settings
from voxpull.domain.errors import InvalidInputError
from voxpull.domain.models import (
    JobErrorInfo, JobResult, JobStage, JobStatus, MediaInfo, MediaKind,
    Transcript, TranscriptSegment,
)


async def wait_for_batch(service, batch_id):
    async with asyncio.timeout(3):
        while True:
            jobs = service.batch_jobs(service.get_batch(batch_id))
            if all(job.status in {JobStatus.COMPLETED, JobStatus.FAILED} for job in jobs):
                return jobs
            await asyncio.sleep(0.005)


def test_batch_share_text_deduplication_and_limit():
    urls, duplicates = extract_batch_urls(
        "复制分享 https://www.douyin.com/video/123。\n"
        "https://www.douyin.com/video/456\nhttps://www.douyin.com/video/123"
    )
    assert urls == ["https://www.douyin.com/video/123", "https://www.douyin.com/video/456"]
    assert duplicates == 1
    with pytest.raises(InvalidInputError):
        extract_batch_urls("没有链接")
    with pytest.raises(InvalidInputError):
        extract_batch_urls("\n".join(f"https://example.test/{i}" for i in range(201)))


async def test_batch_of_53_uses_bounded_queue_and_keeps_going_after_failure():
    repository = InMemoryJobRepository()

    class Pipeline:
        active = 0
        maximum = 0
        fail = True

        async def execute(self, job_id):
            self.active += 1
            self.maximum = max(self.maximum, self.active)
            try:
                job = repository.get(job_id)
                repository.update(job_id, status=JobStatus.RUNNING, stage=JobStage.DOWNLOADING)
                await asyncio.sleep(0.001)
                if job.content.endswith("/7") and self.fail:
                    raise RuntimeError("deliberate failure")
                repository.update(job_id, status=JobStatus.COMPLETED, stage=JobStage.COMPLETED, progress=100)
            finally:
                self.active -= 1

    pipeline = Pipeline()
    service = JobService(repository, pipeline, max_queue=1, max_concurrency=2)
    await service.start()
    try:
        batch = service.submit_batch([f"https://example.test/{i}" for i in range(53)], "zh", False)
        assert service.has_active_jobs()
        jobs = await wait_for_batch(service, batch.id)
        assert sum(job.status is JobStatus.COMPLETED for job in jobs) == 52
        assert sum(job.status is JobStatus.FAILED for job in jobs) == 1
        assert pipeline.maximum == 2
        successful_ids = {job.id for job in jobs if job.status is JobStatus.COMPLETED}
        pipeline.fail = False
        retried = service.retry_batch(batch.id)
        assert retried.id == batch.id
        jobs = await wait_for_batch(service, batch.id)
        assert len(jobs) == 53
        assert all(job.status is JobStatus.COMPLETED for job in jobs)
        assert successful_ids.issubset({job.id for job in jobs})
    finally:
        await service.stop()


async def test_stopping_batch_clears_pending_and_marks_unfinished_jobs_failed():
    repository = InMemoryJobRepository()
    started = asyncio.Event()

    class Pipeline:
        async def execute(self, job_id):
            repository.update(job_id, status=JobStatus.RUNNING, stage=JobStage.DOWNLOADING)
            started.set()
            await asyncio.Event().wait()

    service = JobService(repository, Pipeline(), max_queue=1, max_concurrency=1)
    await service.start()
    batch = service.submit_batch([f"https://example.test/{i}" for i in range(53)], "zh", False)
    await asyncio.wait_for(started.wait(), timeout=1)
    await service.stop()
    assert all(job.status is JobStatus.FAILED for job in service.batch_jobs(batch))
    assert not service.has_active_jobs()
    await asyncio.wait_for(service.queue.join(), timeout=1)


async def test_batch_api_results_archive_and_failed_only_retry(tmp_path: Path):
    settings = Settings(
        host="127.0.0.1", port=8000, data_dir=tmp_path / "data",
        ffmpeg_bin="ffmpeg",
        max_queue=1, browser_timeout_seconds=1, download_timeout_seconds=1,
        ffmpeg_timeout_seconds=1,
    )
    app = create_app(settings)
    service = app.state.container.job_service

    class Pipeline:
        fail = True

        async def execute(self, job_id):
            job = service.repository.get(job_id)
            service.repository.update(job_id, status=JobStatus.RUNNING, stage=JobStage.DOWNLOADING)
            if job.content.endswith("/fail") and self.fail:
                service.repository.update(
                    job_id, status=JobStatus.FAILED, stage=JobStage.FAILED,
                    error=JobErrorInfo("download_failed", "测试下载失败", True),
                )
                return
            cover = tmp_path / f"{job_id}.jpg"
            cover.write_bytes(b"jpeg cover")
            service.repository.update(
                job_id, status=JobStatus.COMPLETED, stage=JobStage.COMPLETED, progress=100,
                result=JobResult(
                    media=MediaInfo(job_id, "中文原始标题", MediaKind.VIDEO, "video.mp4", "/unused/video.mp4", False, cover_path=str(cover)),
                    transcript=Transcript("中文逐字稿", (TranscriptSegment(0, 1000, "中文逐字稿"),), "zh"),
                ),
            )

    pipeline = Pipeline()
    service.pipeline = pipeline
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            accepted = await client.post("/api/batches", json={"content": "\n".join([
                "https://example.test/one", "https://example.test/fail",
                "https://example.test/one", "https://example.test/two",
            ]), "save_video": False})
            assert accepted.status_code == 202
            batch_id = accepted.json()["id"]
            await wait_for_batch(service, batch_id)
            response = (await client.get(f"/api/batches/{batch_id}")).json()
            assert response["total"] == 3 and response["duplicate_count"] == 1
            assert response["completed"] == 2 and response["failed"] == 1
            assert response["progress"] == 100
            assert "result" not in response["jobs"][0]
            archive = await client.get(f"/api/batches/{batch_id}/archive")
            assert archive.status_code == 200
            with zipfile.ZipFile(io.BytesIO(archive.content)) as files:
                names = files.namelist()
                assert len([n for n in names if n.endswith("逐字稿.txt")]) == 2
                assert len([n for n in names if n.endswith("封面.jpg")]) == 2
                title_name = next(n for n in names if n.endswith("标题.txt"))
                assert files.read(title_name).decode() == "中文原始标题"
                manifest = json.loads(files.read("批处理清单.json"))
                assert manifest["failed"] == 1
            pipeline.fail = False
            assert (await client.post(f"/api/batches/{batch_id}/retry")).status_code == 202
            await wait_for_batch(service, batch_id)
            final = (await client.get(f"/api/batches/{batch_id}")).json()
            assert final["completed"] == 3 and final["failed"] == 0
            assert (await client.get("/api/batches/not-found")).status_code == 404


async def test_gallery_archive_contains_source_caption_without_fake_subtitles(tmp_path):
    from test_api import make_settings
    app = create_app(make_settings(tmp_path))
    service = app.state.container.job_service

    class GalleryPipeline:
        async def execute(self, ident):
            service.repository.update(ident, status=JobStatus.RUNNING, stage=JobStage.DOWNLOADING)
            media = MediaInfo("gallery", "图文标题", MediaKind.IMAGES, "gallery", "/unused/gallery", True,
                              description="正文\n#话题#")
            service.repository.update(ident, status=JobStatus.COMPLETED, stage=JobStage.COMPLETED,
                                      progress=100, result=JobResult(media))

    service.pipeline = GalleryPipeline()
    async with app.router.lifespan_context(app):
        batch = service.submit_batch(["https://www.xiaohongshu.com/explore/gallery"], "zh", False, extract_txt=False)
        await wait_for_batch(service, batch.id)
        async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
            response = await client.get(f"/api/batches/{batch.id}/archive")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        caption = next(name for name in archive.namelist() if name.endswith("/文案.txt"))
        assert archive.read(caption).decode() == "正文\n#话题#"
        assert not any(name.endswith(("/字幕.srt", "/逐字稿.txt", "/时间轴.txt")) for name in archive.namelist())
