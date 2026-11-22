import asyncio
from httpx import ASGITransport, AsyncClient

from voxpull.app import create_app
from voxpull.domain.models import Job, JobResult, JobStage, JobStatus, MediaInfo, MediaKind
from voxpull.infrastructure.job_records import FileJobRepository, FileJobService
from test_api import make_settings


async def test_optional_txt_api_and_retry_preserve_false(tmp_path):
    app = create_app(make_settings(tmp_path))
    service = app.state.container.job_service

    class Pipeline:
        async def execute(self, job_id):
            job = service.get(job_id)
            assert job.extract_txt is False
            service.repository.update(job_id, status=JobStatus.RUNNING)
            service.repository.update(job_id, status=JobStatus.FAILED, stage=JobStage.FAILED)

    service.pipeline = Pipeline()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
            assert (await client.get("/api/jobs/capabilities")).json()["extract_txt"]
            response = await client.post("/api/jobs", json={"content": "https://www.douyin.com/video/123", "extract_txt": False})
            assert response.status_code == 202
            await service.queue.join()
            ident = response.json()["job_id"]
            response = await client.post(f"/api/jobs/{ident}/retry")
            assert response.status_code == 202
            await service.queue.join()
            assert service.get(response.json()["job_id"]).extract_txt is False


async def test_records_and_batch_survive_worker_restart(tmp_path):
    root = tmp_path / "records"
    repo = FileJobRepository(root)

    class Pipeline:
        async def execute(self, job_id):
            repo.update(job_id, status=JobStatus.RUNNING)
            media = MediaInfo("123", "test", MediaKind.VIDEO, "a.mp4", "/unused/a.mp4", True)
            repo.update(job_id, status=JobStatus.COMPLETED, stage=JobStage.COMPLETED,
                        progress=100, result=JobResult(media))

    service = FileJobService(repo, Pipeline(), 10)
    await service.start()
    batch = service.submit_batch(["https://example.test/1", "https://example.test/2"], "auto", True, extract_txt=False)
    async with asyncio.timeout(2):
        while any(job.status not in {JobStatus.COMPLETED, JobStatus.FAILED} for job in service.batch_jobs(batch)):
            await asyncio.sleep(.001)
    await service.queue.join()
    original = service.batch_jobs(batch)
    await service.stop()
    restored = FileJobRepository(root)
    second = FileJobService(restored, None, 10)
    await second.start()
    try:
        assert second.get_batch(batch.id) == batch
        assert second.batch_jobs(batch) == original
        assert all(not job.extract_txt for job in original)
        assert all(path.stat().st_mode & 0o777 == 0o600 for path in root.glob("*.json"))
    finally:
        await second.stop()


def test_interrupted_record_becomes_retryable_without_losing_options(tmp_path):
    repo = FileJobRepository(tmp_path)
    repo.add(Job("pending", "https://example.test/video", "auto", extract_txt=False))
    restored = FileJobRepository(tmp_path)
    restored.load()
    job = restored.get("pending")
    assert job.status is JobStatus.FAILED
    assert job.error.retryable
    assert job.content == "https://example.test/video" and job.extract_txt is False


def test_gallery_caption_survives_record_reload(tmp_path):
    from voxpull.api.schemas import job_to_response
    repo = FileJobRepository(tmp_path)
    media = MediaInfo("gallery", "标题", MediaKind.IMAGES, "gallery", "/unused/gallery", True,
                      description="正文\n#话题#", description_path="/unused/gallery/文案.txt")
    repo.add(Job("gallery", "https://www.xiaohongshu.com/explore/gallery", "zh",
                 status=JobStatus.COMPLETED, result=JobResult(media), extract_txt=False))
    restored = FileJobRepository(tmp_path)
    restored.load()
    job = restored.get("gallery")
    assert job.result.media == media
    response = job_to_response(job)
    assert response.result.transcript is None
    assert response.result.media.description == "正文\n#话题#"
