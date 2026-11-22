from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from voxpull.api.jobs import router
from voxpull.api.schemas import job_to_response
from voxpull.domain.models import Job, JobResult, MediaInfo, MediaKind
from voxpull.infrastructure.video_preview import create_preview_bridge


def preview_app(tmp_path):
    path = tmp_path / "video.mp4"
    path.write_bytes(bytes(range(256)) * 8)
    media = MediaInfo("video", "标题", MediaKind.VIDEO, path.name, str(path), True)
    job = Job("saved", "https://example.test/video", "zh", result=JobResult(media))
    jobs = {"saved": job}
    jobs["temporary"] = replace(job, id="temporary", result=JobResult(replace(media, saved=False)))
    jobs["image"] = replace(job, id="image", result=JobResult(replace(media, kind=MediaKind.IMAGES)))
    jobs["missing"] = replace(job, id="missing", result=JobResult(
        replace(media, absolute_path=str(tmp_path / "missing.mp4"))
    ))
    app = FastAPI()
    app.state.container = SimpleNamespace(job_service=SimpleNamespace(get=jobs.get))
    app.include_router(router)
    return app, path, jobs


async def test_video_preview_supports_seeking_head_and_invalid_ranges(tmp_path):
    app, path, _ = preview_app(tmp_path)
    original = path.read_bytes()
    stat = path.stat()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        response = await client.get("/api/jobs/saved/video", headers={"Range": "bytes=4-11"})
        assert response.status_code == 206
        assert response.content == original[4:12]
        assert response.headers["content-range"] == f"bytes 4-11/{len(original)}"
        assert response.headers["content-type"] == "video/mp4"
        assert response.headers["content-disposition"].startswith("inline;")
        head = await client.head("/api/jobs/saved/video")
        assert head.status_code == 200
        assert not head.content
        assert int(head.headers["content-length"]) == len(original)
        bad = await client.get("/api/jobs/saved/video", headers={"Range": "bytes=9000-"})
        assert bad.status_code == 416
    assert path.read_bytes() == original
    assert path.stat().st_mtime_ns == stat.st_mtime_ns


@pytest.mark.parametrize("job_id", ["temporary", "image", "missing", "unknown"])
async def test_preview_rejects_unsaved_images_missing_files_and_unknown_jobs(tmp_path, job_id):
    app, _, _ = preview_app(tmp_path)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        assert (await client.get(f"/api/jobs/{job_id}/video")).status_code == 404


def test_only_saved_videos_advertise_native_preview_url(tmp_path):
    _, _, jobs = preview_app(tmp_path)
    assert job_to_response(jobs["saved"]).result.media.video_url == "/api/jobs/saved/video"
    assert job_to_response(jobs["temporary"]).result.media.video_url is None
    assert job_to_response(jobs["image"]).result.media.video_url is None


@pytest.mark.parametrize("job_id,expected", [("saved", 206), ("temporary", 404), ("image", 404)])
async def test_live_session_bridge_reads_job_result_and_serves_ranges(tmp_path, job_id, expected):
    _, path, jobs = preview_app(tmp_path)
    calls = []

    def main_api(request):
        calls.append((request.method, request.url.path))
        return httpx.Response(200, json=job_to_response(jobs[job_id]).model_dump(mode="json"))

    app = create_preview_bridge(18765, 1)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(main_api), base_url="http://127.0.0.1:18765"
    ) as upstream:
        app.state.client = upstream
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
            response = await client.get(f"/api/jobs/{job_id}/video", headers={"Range": "bytes=0-7"})
            assert response.status_code == expected
            if expected == 206:
                assert response.content == path.read_bytes()[:8]
    assert calls == [("GET", f"/api/jobs/{job_id}")]


async def test_native_publication_reads_captured_timestamp_without_network(tmp_path):
    app, _, jobs = preview_app(tmp_path)
    jobs["saved"].result = JobResult(replace(jobs["saved"].result.media, published_at=1735689600))
    app.state.publication_lookup = SimpleNamespace(get=AsyncMock())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        assert (await client.get("/api/jobs/saved/publication")).json() == {"published_at": 1735689600}
    app.state.publication_lookup.get.assert_not_awaited()


async def test_legacy_publication_bridge_allows_only_local_app_origin(tmp_path):
    _, _, jobs = preview_app(tmp_path)
    app = create_preview_bridge(18765, 1)
    app.state.publication_lookup = SimpleNamespace(get=AsyncMock(return_value=1735689600))
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _r: httpx.Response(
        200, json=job_to_response(jobs["saved"]).model_dump(mode="json")
    )), base_url="http://127.0.0.1:18765") as upstream:
        app.state.client = upstream
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
            response = await client.get("/api/jobs/saved/publication", headers={"Origin": "http://127.0.0.1:18765"})
            assert response.json() == {"published_at": 1735689600}
            assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:18765"
            other = await client.get("/api/jobs/saved/publication", headers={"Origin": "https://example.test"})
            assert "access-control-allow-origin" not in other.headers
