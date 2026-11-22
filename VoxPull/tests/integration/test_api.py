import asyncio
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from voxpull.app import create_app
from voxpull.application.summary_service import SummaryService
from voxpull.config import Settings
from voxpull.domain.errors import CookieMissingError
from voxpull.domain.models import (
    Job,
    JobResult,
    JobStage,
    JobStatus,
    MediaAssetInfo,
    MediaAssetKind,
    MediaInfo,
    MediaKind,
    SummaryProviderStatus,
    SummaryStyle,
    Transcript,
    TranscriptSegment,
    VideoSummary,
)


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        host="127.0.0.1",
        port=8000,
        data_dir=tmp_path / "data",
        model_path=tmp_path / "models" / "model.bin",
        ffmpeg_bin="ffmpeg",
        whisper_bin="whisper-cli",
        max_queue=2,
        browser_timeout_seconds=1,
        download_timeout_seconds=1,
        ffmpeg_timeout_seconds=1,
        whisper_timeout_seconds=1,
    )


class FakeSummaryProvider:
    def __init__(self) -> None:
        self.configured = False
        self.base_url = ""
        self.model = ""
        self.configured_payloads: list[tuple[str, str, str]] = []
        self.summary_requests: list[tuple[str, SummaryStyle]] = []
        self.model_list_requests: list[tuple[str, str]] = []

    def status(self) -> SummaryProviderStatus:
        return SummaryProviderStatus(
            configured=self.configured,
            base_url=self.base_url,
            model=self.model,
        )

    async def configure(self, base_url: str, api_key: str, model: str) -> None:
        self.configured = True
        self.base_url = base_url
        self.model = model
        self.configured_payloads.append((base_url, api_key, model))

    async def clear(self) -> None:
        self.configured = False
        self.base_url = ""
        self.model = ""

    async def list_models(self, base_url: str, api_key: str) -> list[str]:
        self.model_list_requests.append((base_url, api_key))
        return ["model-b", "model-a"]

    async def summarize(
        self,
        text: str,
        style: SummaryStyle,
    ) -> VideoSummary:
        self.summary_requests.append((text, style))
        return VideoSummary(markdown="## 一句话总结\n\n总结概要\n\n## 核心要点\n\n- 核心要点")


def install_fake_summary_provider(app, provider: FakeSummaryProvider) -> None:
    container = app.state.container
    container.summary_service = SummaryService(
        container.job_service.repository,
        provider,
        provider,
        max_input_chars=container.settings.summary_max_input_chars,
        max_concurrency=container.settings.summary_concurrency,
    )


def completed_video_job(job_id: str = "completed-video") -> Job:
    return Job(
        id=job_id,
        content="https://example.test/video",
        language="zh",
        status=JobStatus.COMPLETED,
        stage=JobStage.COMPLETED,
        progress=100,
        result=JobResult(
            media=MediaInfo(
                id="video",
                title="测试视频",
                kind=MediaKind.VIDEO,
                filename="video.mp4",
                absolute_path="/tmp/video.mp4",
                saved=True,
            ),
            transcript=Transcript(
                text="原始文案",
                segments=(TranscriptSegment(12_000, 15_000, "第一段"),),
                detected_language="zh",
            ),
        ),
    )


async def test_cover_and_title_are_available_without_retaining_video(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))
    cover = tmp_path / "cover.jpg"
    title = tmp_path / "title.txt"
    cover.write_bytes(b"jpeg cover")
    title.write_text("视频原始标题 #中文", encoding="utf-8")
    job = completed_video_job("video-details")
    job.result = replace(job.result, media=replace(
        job.result.media, saved=False, cover_path=str(cover), title_path=str(title)
    ))
    app.state.container.job_service.repository.add(job)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            detail = (await client.get("/api/jobs/video-details")).json()["result"]["media"]
            assert detail["cover_url"] == "/api/jobs/video-details/cover"
            assert detail["title_url"] == "/api/jobs/video-details/title"
            response = await client.get(detail["cover_url"])
            assert response.content == b"jpeg cover"
            assert response.headers["content-type"] == "image/jpeg"
            response = await client.get(detail["title_url"])
            assert response.text == "视频原始标题 #中文"
            assert response.headers["content-type"].startswith("text/plain")
            cover.unlink()
            assert (await client.get(detail["cover_url"])).status_code == 404
            assert (await client.get("/api/jobs/missing/cover")).status_code == 404


async def test_job_api_and_static_page(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))
    app.state.container.browser.acquire = AsyncMock(side_effect=CookieMissingError())
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            page = await client.get("/")
            assert page.status_code == 200
            assert page.headers["cache-control"] == "no-cache"
            assert "/static/styles.css?v=" in page.text
            assert "/static/app.js?v=" in page.text
            assert 'class="skip-link"' in page.text
            assert 'class="signal-chain"' in page.text
            assert 'id="share-content-error"' in page.text
            assert 'id="settings-open"' in page.text
            assert 'role="tab"' in page.text
            assert 'id="view-tab-summary"' in page.text
            assert 'id="summary-generate"' in page.text
            assert 'id="summary-markdown"' in page.text
            assert 'id="summary-download"' in page.text
            assert 'class="summary-style' not in page.text
            assert "要点速览" not in page.text
            assert "详细段落" not in page.text
            assert page.text.index('id="summary-copy"') < page.text.index('id="summary-download"')
            assert page.text.index('id="summary-download"') < page.text.index('id="summary-regenerate"')
            assert 'data-style="chapters"' not in page.text
            assert 'id="summary-chapters"' not in page.text
            assert 'id="summary-config-dialog"' in page.text
            assert 'id="summary-config-model-status"' in page.text
            assert 'id="summary-config-model-trigger"' in page.text
            assert 'id="summary-config-model-list"' in page.text
            assert 'id="summary-config-key-toggle"' in page.text
            assert 'class="summary-preset"' in page.text
            assert 'id="auto-summary-toggle"' in page.text
            assert 'id="progress-panel"' not in page.text
            assert 'id="auth-chrome"' not in page.text
            assert 'id="image-grid"' in page.text
            assert 'id="image-viewer"' in page.text
            assert 'id="image-viewer-previous"' in page.text
            assert 'id="image-viewer-zoom-value"' in page.text
            assert 'id="image-viewer-video"' in page.text
            assert 'id="image-viewer-live-replay"' in page.text
            assert 'id="image-viewer-title"' in page.text
            assert 'class="image-viewer-media-controls"' in page.text
            static = await client.get("/static/styles.css?v=20260718-2")
            assert static.headers["cache-control"] == "no-cache"
            app_static = await client.get("/static/app.js?v=20260719-12")
            assert "/open-location" in app_static.text
            assert "playback_url" in app_static.text
            assert 'addEventListener("mouseenter"' in app_static.text
            assert (await client.get("/api/jobs/missing")).status_code == 404

            accepted = await client.post(
                "/api/jobs",
                json={"content": "https://v.douyin.com/demo/", "language": "zh"},
            )
            assert accepted.status_code == 202
            job_id = accepted.json()["job_id"]

            for _ in range(20):
                response = await client.get(f"/api/jobs/{job_id}")
                if response.json()["status"] == "failed":
                    break
                await asyncio.sleep(0.01)
            payload = response.json()
            assert payload["status"] == "failed"
            assert payload["error"]["code"] == "cookie_missing"

            invalid = await client.post("/api/jobs", json={"content": "x", "language": "english"})
            assert invalid.status_code == 422


async def test_storage_location_api_updates_and_persists_selected_directory(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    selected_root = tmp_path / "VoxPull Media"
    selected_root.mkdir()
    app = create_app(settings)

    class SelectedDirectoryPicker:
        async def choose(self, initial_directory: Path) -> Path:
            assert initial_directory == settings.data_dir.resolve()
            return selected_root

    app.state.container.directory_picker = SelectedDirectoryPicker()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/storage/location")

    assert response.status_code == 200
    assert response.json() == {
        "changed": True,
        "media_root_path": str(selected_root.resolve()),
        "video_storage_path": str((selected_root / "videos").resolve()),
        "image_storage_path": str((selected_root / "images").resolve()),
    }
    assert (selected_root / "videos").is_dir()
    assert (selected_root / "images").is_dir()
    assert (selected_root / "work").is_dir()
    assert app.state.container.storage.work_root == selected_root / "work"

    restored_app = create_app(settings)
    assert restored_app.state.container.storage.work_root == selected_root / "work"
    assert restored_app.state.container.storage.media_root == selected_root.resolve()


async def test_storage_location_api_keeps_path_when_picker_is_cancelled(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    app = create_app(settings)

    class CancelledDirectoryPicker:
        async def choose(self, _initial_directory: Path) -> None:
            return None

    app.state.container.directory_picker = CancelledDirectoryPicker()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/storage/location")

    assert response.status_code == 200
    assert response.json()["changed"] is False
    assert response.json()["media_root_path"] == str(settings.data_dir.resolve())


async def test_storage_location_api_rejects_changes_during_active_job(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))
    app.state.container.job_service.has_active_jobs = lambda: True
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/storage/location")

    assert response.status_code == 409
    assert response.json()["code"] == "storage_location_failed"


async def test_open_job_location_uses_saved_media_path(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))
    media_path = tmp_path / "images" / "gallery"
    media_path.mkdir(parents=True)
    job = Job(
        id="completed-gallery",
        content="https://example.test/gallery",
        language="zh",
        status=JobStatus.COMPLETED,
        stage=JobStage.COMPLETED,
        progress=100,
        result=JobResult(
            media=MediaInfo(
                id="gallery",
                title="测试图集",
                kind=MediaKind.IMAGES,
                filename=media_path.name,
                absolute_path=str(media_path),
                saved=True,
                asset_count=2,
            )
        ),
    )
    app.state.container.job_service.repository.add(job)
    opened_paths: list[Path] = []

    class RecordingPathOpener:
        async def reveal(self, path: Path) -> None:
            opened_paths.append(path)

    app.state.container.path_opener = RecordingPathOpener()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/jobs/completed-gallery/open-location")

    assert response.status_code == 200
    assert response.json() == {"opened": True}
    assert opened_paths == [media_path]


async def test_live_motion_asset_is_exposed_for_inline_range_playback(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))
    media_path = tmp_path / "images" / "live-gallery"
    media_path.mkdir(parents=True)
    image_path = media_path / "001.jpg"
    motion_path = media_path / "001.live.mp4"
    image_path.write_bytes(b"image")
    motion_bytes = b"\x00\x00\x00\x18ftypisom-live-motion"
    motion_path.write_bytes(motion_bytes)
    job = Job(
        id="completed-live-gallery",
        content="https://example.test/live-gallery",
        language="zh",
        status=JobStatus.COMPLETED,
        stage=JobStage.COMPLETED,
        progress=100,
        result=JobResult(
            media=MediaInfo(
                id="live-gallery",
                title="测试 Live 图",
                kind=MediaKind.IMAGES,
                filename=media_path.name,
                absolute_path=str(media_path),
                saved=True,
                asset_count=1,
                live_photo_count=1,
                assets=(
                    MediaAssetInfo(
                        index=1,
                        kind=MediaAssetKind.LIVE_MOTION,
                        filename=motion_path.name,
                        absolute_path=str(motion_path),
                    ),
                    MediaAssetInfo(
                        index=1,
                        kind=MediaAssetKind.IMAGE,
                        filename=image_path.name,
                        absolute_path=str(image_path),
                    ),
                ),
            )
        ),
    )
    app.state.container.job_service.repository.add(job)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            job_response = await client.get("/api/jobs/completed-live-gallery")
            motion_response = await client.get(
                "/api/jobs/completed-live-gallery/assets/0",
                headers={"Range": "bytes=4-11"},
            )

    assets = job_response.json()["result"]["media"]["assets"]
    assert assets[0]["preview_url"] is None
    assert assets[0]["playback_url"] == "/api/jobs/completed-live-gallery/assets/0"
    assert assets[1]["preview_url"] == "/api/jobs/completed-live-gallery/assets/1"
    assert assets[1]["playback_url"] is None
    assert motion_response.status_code == 206
    assert motion_response.content == motion_bytes[4:12]
    assert motion_response.headers["content-type"] == "video/mp4"
    assert motion_response.headers["accept-ranges"] == "bytes"
    assert motion_response.headers["content-disposition"].startswith("inline;")


async def test_summary_config_and_generation_api_with_openai_compatible_provider(
    tmp_path: Path,
) -> None:
    app = create_app(make_settings(tmp_path))
    provider = FakeSummaryProvider()
    install_fake_summary_provider(app, provider)
    app.state.container.job_service.repository.add(completed_video_job())

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            initial = await client.get("/api/summary/config")
            assert initial.status_code == 200
            assert initial.json() == {"configured": False, "base_url": "", "model": ""}

            unavailable = await client.post(
                "/api/jobs/completed-video/summary",
                json={"style": "brief", "transcript_text": "编辑后的文案"},
            )
            assert unavailable.status_code == 409
            assert unavailable.json()["code"] == "ai_summary_unavailable"

            rejected = await client.put(
                "/api/summary/config",
                json={
                    "base_url": "not-a-url",
                    "api_key": "some-key",
                    "model": "any-model",
                },
            )
            assert rejected.status_code == 422
            assert provider.configured_payloads == []

            missing_key = await client.put(
                "/api/summary/config",
                json={
                    "base_url": "https://example.test/v1",
                    "api_key": "",
                    "model": "any-model",
                },
            )
            assert missing_key.status_code == 422
            assert provider.configured_payloads == []

            configured = await client.put(
                "/api/summary/config",
                json={
                    "base_url": "https://example.test/v1/",
                    "api_key": "secret-key",
                    "model": "any-model",
                },
            )
            assert configured.status_code == 200
            assert configured.json() == {
                "configured": True,
                "base_url": "https://example.test/v1",
                "model": "any-model",
            }
            assert "secret-key" not in configured.text

            models = await client.post(
                "/api/summary/models",
                json={"base_url": "https://example.test/v1/", "api_key": "secret-key"},
            )
            assert models.status_code == 200
            assert models.json() == {"models": ["model-b", "model-a"]}
            assert provider.model_list_requests == [("https://example.test/v1", "secret-key")]

            invalid_models = await client.post(
                "/api/summary/models",
                json={"base_url": "ftp://example.test", "api_key": "secret-key"},
            )
            assert invalid_models.status_code == 422

            summary = await client.post(
                "/api/jobs/completed-video/summary",
                json={"style": "detailed", "transcript_text": "校对后的当前文案"},
            )
            assert summary.status_code == 200
            payload = summary.json()
            assert payload["markdown"] == "## 一句话总结\n\n总结概要\n\n## 核心要点\n\n- 核心要点"
            assert "chapters" not in payload
            assert payload["style"] == "detailed"
            assert payload["model"] == "any-model"
            assert provider.summary_requests == [("校对后的当前文案", SummaryStyle.DETAILED)]

            removed_style = await client.post(
                "/api/jobs/completed-video/summary",
                json={"style": "chapters", "transcript_text": "校对后的当前文案"},
            )
            assert removed_style.status_code == 422

            cleared = await client.delete("/api/summary/config")
            assert cleared.status_code == 204
            assert not provider.configured


async def test_open_location_reveals_work_folder_even_without_retained_video(tmp_path):
    app = create_app(make_settings(tmp_path))
    folder = tmp_path / "videos" / "作品标题"
    folder.mkdir(parents=True)
    title = folder / "标题.txt"
    title.write_text("作品标题")
    opened = []

    class Opener:
        async def reveal(self, path):
            opened.append(path)

    app.state.container.path_opener = Opener()
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        for saved in [True, False]:
            job = completed_video_job(f"open-{saved}")
            job.result = replace(job.result, media=replace(job.result.media,
                absolute_path=str(folder / "视频.mp4"), title_path=str(title), saved=saved))
            app.state.container.job_service.repository.add(job)
            response = await client.post(f"/api/jobs/{job.id}/open-location")
            assert response.status_code == 200
    assert opened == [folder, folder]


async def test_gallery_cover_response_uses_its_actual_image_format(tmp_path):
    app = create_app(make_settings(tmp_path))
    cover = tmp_path / "封面.png"
    cover.write_bytes(b"png cover")
    job = completed_video_job("gallery-cover")
    job.result = replace(job.result, media=replace(job.result.media,
        kind=MediaKind.IMAGES, cover_path=str(cover)))
    app.state.container.job_service.repository.add(job)
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.get(f"/api/jobs/{job.id}/cover")
        assert response.status_code == 200 and response.content == cover.read_bytes()
        assert response.headers["content-type"] == "image/png"
