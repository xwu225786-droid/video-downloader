from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from voxpull.api.jobs import router
from voxpull.api.schemas import job_to_response
from voxpull.application.job_service import InMemoryJobRepository, JobService
from voxpull.domain.errors import InvalidInputError
from voxpull.domain.models import Job, JobResult, JobStage, JobStatus, MediaInfo, MediaKind
from voxpull.infrastructure.video_preview import create_preview_bridge


def app_with_files(tmp_path):
    repo = InMemoryJobRepository()
    video = tmp_path / "video.mp4"
    cover = tmp_path / "video.cover.jpg"
    title = tmp_path / "video.title.txt"
    for path in (video, cover, title):
        path.write_bytes(b"original")
    media = MediaInfo("123", "title", MediaKind.VIDEO, video.name, str(video), True,
                      cover_path=str(cover), title_path=str(title))
    done = Job("done", "https://www.douyin.com/video/123", "zh", status=JobStatus.COMPLETED,
               stage=JobStage.COMPLETED, result=JobResult(media))
    repo.add(done)
    repo.add(replace(done, id="shared"))
    repo.add(Job("failed", "https://www.douyin.com/video/456", "auto", False,
                 status=JobStatus.FAILED, stage=JobStage.FAILED))
    repo.add(Job("running", "https://www.douyin.com/video/789", "zh", status=JobStatus.RUNNING))
    service = JobService(repo, None, 10)
    app = FastAPI()
    app.state.container = SimpleNamespace(job_service=service)
    app.include_router(router)
    return app, service, (video, cover, title)


async def test_retry_only_failed_job_preserves_options_and_other_jobs(tmp_path):
    app, service, paths = app_with_files(tmp_path)
    before = service.get("done")

    class Pipeline:
        async def execute(self, job_id):
            service.repository.update(job_id, status=JobStatus.RUNNING)
            service.repository.update(job_id, status=JobStatus.COMPLETED)

    service.pipeline = Pipeline()
    await service.start()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
            response = await client.post("/api/jobs/failed/retry")
            assert response.status_code == 202
            new_id = response.json()["job_id"]
            assert new_id != "failed"
            await service.queue.join()
            retried = service.get(new_id)
            assert (retried.content, retried.language, retried.save_video) == (
                "https://www.douyin.com/video/456", "auto", False,
            )
            assert service.get("failed").status is JobStatus.FAILED
            assert service.get("done") == before
            with pytest.raises(InvalidInputError):
                await client.post("/api/jobs/done/retry")
            assert (await client.post("/api/jobs/unknown/retry")).status_code == 404
    finally:
        await service.stop()
    assert all(path.read_bytes() == b"original" for path in paths)


async def test_delete_shared_files_then_delete_explicit_selected_files_only(tmp_path):
    app, _, paths = app_with_files(tmp_path)
    unrelated = tmp_path / "other.mp4"
    unrelated.write_bytes(b"unrelated")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        response = await client.post("/api/jobs/files/delete", json={
            "job_ids": ["done"], "protect_job_ids": ["shared"],
        })
        assert response.json() == {"deleted_files": 0, "shared_files": 3, "missing_files": 0}
        assert all(path.is_file() for path in paths)
        response = await client.post("/api/jobs/files/delete", json={"job_ids": ["done", "shared"]})
        assert response.json()["deleted_files"] == 3
        assert all(not path.exists() for path in paths)
        assert unrelated.read_bytes() == b"unrelated"
        response = await client.post("/api/jobs/files/delete", json={"job_ids": ["done"]})
        assert response.json()["missing_files"] == 3


@pytest.mark.parametrize("payload,status", [
    ({"job_ids": ["unknown"]}, 404),
    ({"job_ids": ["running"]}, 409),
    ({"job_ids": ["done"], "protect_job_ids": ["running"]}, 409),
    ({"job_ids": []}, 422),
])
async def test_invalid_deletions_preserve_all_files(tmp_path, payload, status):
    app, _, paths = app_with_files(tmp_path)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        assert (await client.post("/api/jobs/files/delete", json=payload)).status_code == status
    assert all(path.read_bytes() == b"original" for path in paths)


async def test_deletion_rejects_symlinks_and_foreign_origins(tmp_path):
    app, _, paths = app_with_files(tmp_path)
    target = tmp_path / "target.mp4"
    target.write_bytes(b"target")
    paths[0].unlink()
    paths[0].symlink_to(target)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        assert (await client.post("/api/jobs/files/delete", json={"job_ids": ["done"]})).status_code == 409
        assert (await client.post("/api/jobs/files/delete", json={"job_ids": ["done"]},
                                  headers={"Origin": "https://foreign.test"})).status_code == 403
    assert target.read_bytes() == b"target"
    assert paths[1].read_bytes() == b"original"


async def test_failed_task_can_delete_recorded_files_without_a_result(tmp_path):
    app, service, paths = app_with_files(tmp_path)
    failed_file = tmp_path / "failed-video.mp4"
    failed_file.write_bytes(b"downloaded before transcription failed")
    service.repository.update("failed", metadata={"source_files": [str(failed_file)]})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        response = await client.post("/api/jobs/files/delete", json={"job_ids": ["failed"]})
        assert response.json()["deleted_files"] == 1
    assert not failed_file.exists()
    assert all(path.read_bytes() == b"original" for path in paths)


async def test_live_bridge_deletes_only_server_recorded_files_from_local_app(tmp_path):
    _, service, paths = app_with_files(tmp_path)
    calls = []

    def upstream(request):
        calls.append(request.url.path)
        return httpx.Response(200, json=job_to_response(service.get("done")).model_dump(mode="json"))

    app = create_preview_bridge(18765, 1)
    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream), base_url="http://main") as proxy:
        app.state.client = proxy
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
            for origin in (None, "https://foreign.test"):
                headers = {"Origin": origin} if origin else {}
                assert (await client.post("/api/jobs/files/delete", headers=headers,
                                          json={"job_ids": ["done"]})).status_code == 403
            assert not calls
            response = await client.post("/api/jobs/files/delete", json={"job_ids": ["done"]},
                                         headers={"Origin": "http://127.0.0.1:18765"})
            assert response.json()["deleted_files"] == 3
            assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:18765"
    assert calls == ["/api/jobs/done"]
    assert all(not path.exists() for path in paths)
