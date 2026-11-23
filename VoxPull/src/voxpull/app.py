from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from voxpull.api import auth, batches, feishu, jobs, material_search, material_tags, summaries, system
from voxpull.api.schemas import ErrorResponse
from voxpull.application.auth_service import AuthService
from voxpull.application.job_service import JobService
from voxpull.application.feishu_service import FeishuService
from voxpull.application.pipeline import TranscriptionPipeline
from voxpull.application.summary_service import SummaryService
from voxpull.application.system_service import SystemService
from voxpull.config import Settings
from voxpull.domain.errors import VoxPullError
from voxpull.infrastructure.audio import FfmpegAudioExtractor
from voxpull.infrastructure.cover import FfmpegCoverExtractor
from voxpull.infrastructure.browser import PlaywrightBrowser
from voxpull.infrastructure.downloader import YtDlpDownloader
from voxpull.infrastructure.douyin_guest import DouyinGuestReader
from voxpull.infrastructure.summarizer import OpenAICompatibleSummarizer
from voxpull.infrastructure.directory_picker import NativeDirectoryPicker
from voxpull.infrastructure.path_opener import NativePathOpener
from voxpull.infrastructure.processes import ProcessRunner
from voxpull.infrastructure.storage import LocalStorage
from voxpull.infrastructure.system import LocalSystemProbe
from voxpull.infrastructure.transcriber import WhisperCppTranscriber
from voxpull.infrastructure.cloud_transcriber import SelectableTranscriber
from voxpull.api import transcription
from voxpull.infrastructure.job_records import FileJobRepository, FileJobService
from voxpull.logging_config import file_logging_enabled, run_log_retention_scheduler


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    runner: ProcessRunner
    browser: PlaywrightBrowser
    auth_service: AuthService
    system_service: SystemService
    job_service: JobService
    summary_service: SummaryService
    summary_provider: OpenAICompatibleSummarizer
    storage: LocalStorage
    directory_picker: NativeDirectoryPicker
    path_opener: NativePathOpener
    feishu_service: FeishuService | None = None
    transcription_provider: SelectableTranscriber | None = None


_HTTP_STATUS_BY_ERROR = {
    "invalid_input": 422,
    "unsupported_url": 422,
    "cookie_missing": 409,
    "cookie_refresh_required": 409,
    "cookie_check_required": 409,
    "platform_verification_required": 409,
    "platform_access_restricted": 429,
    "queue_full": 429,
    "dependency_missing": 503,
    "task_timeout": 504,
    "browser_failed": 502,
    "download_failed": 502,
    "audio_extraction_failed": 502,
    "cover_extraction_failed": 502,
    "transcription_failed": 502,
    "storage_location_failed": 409,
    "media_location_failed": 409,
    "ai_summary_unavailable": 409,
    "ai_summary_config_busy": 409,
    "ai_summary_not_available": 409,
    "ai_summary_invalid_input": 422,
    "ai_summary_rate_limited": 429,
    "ai_summary_provider_failed": 502,
    "ai_summary_timeout": 504,
    "ai_summary_invalid_response": 502,
}


def build_container(settings: Settings) -> AppContainer:
    settings.ensure_directories()
    runner = ProcessRunner()
    downloader = YtDlpDownloader(
        settings.download_timeout_seconds,
        image_concurrency=settings.download_concurrency,
    )
    browser = PlaywrightBrowser(
        settings.browser_profile_dir,
        settings.storage_state_path,
        settings.browser_timeout_seconds,
        share_fallback=downloader.download_public_douyin_share,
        guest_reader=DouyinGuestReader(settings.browser_timeout_seconds, downloader),
    )
    repository = FileJobRepository(settings.data_dir / "task-records")
    storage = LocalStorage(
        settings.work_dir,
        settings.videos_dir,
        settings.images_dir,
        settings.storage_location_path,
    )
    transcription_provider = SelectableTranscriber(
        WhisperCppTranscriber(runner, settings.whisper_bin, settings.model_path,
                              settings.whisper_timeout_seconds, settings.vad_model_path),
        settings.auth_dir / "transcription.json",
    )
    pipeline = TranscriptionPipeline(
        repository=repository,
        browser=browser,
        downloader=downloader,
        audio_extractor=FfmpegAudioExtractor(
            runner, settings.ffmpeg_bin, settings.ffmpeg_timeout_seconds
        ),
        transcriber=transcription_provider,
        storage=storage,
        cover_extractor=FfmpegCoverExtractor(
            runner, settings.ffmpeg_bin, settings.ffmpeg_timeout_seconds
        ),
        download_concurrency=settings.download_concurrency,
        ffmpeg_concurrency=settings.ffmpeg_concurrency,
        whisper_concurrency=settings.whisper_concurrency,
    )
    summary_provider = OpenAICompatibleSummarizer(
        settings.summary_timeout_seconds,
        config_path=settings.summary_auth_path,
        legacy_config_path=settings.deepseek_auth_path,
    )
    container = AppContainer(
        settings=settings,
        runner=runner,
        browser=browser,
        auth_service=AuthService(browser),
        system_service=SystemService(browser, LocalSystemProbe(settings)),
        job_service=FileJobService(
            repository,
            pipeline,
            settings.max_queue,
            max_concurrency=settings.max_concurrency,
        ),
        summary_service=SummaryService(
            repository,
            summary_provider,
            summary_provider,
            max_input_chars=settings.summary_max_input_chars,
            max_concurrency=settings.summary_concurrency,
        ),
        summary_provider=summary_provider,
        transcription_provider=transcription_provider,
        storage=storage,
        directory_picker=NativeDirectoryPicker(),
        path_opener=NativePathOpener(),
    )
    pipeline.summary_service = container.summary_service
    container.feishu_service = FeishuService(settings.data_dir, container.job_service, storage)
    return container


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    container = build_container(settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.container = container
        logger.info(
            "event=service_starting host=%s port=%s max_concurrency=%s",
            container.settings.host,
            container.settings.port,
            container.settings.max_concurrency,
        )
        removed = container.storage.cleanup_stale_work_dirs()
        if removed:
            logger.info("event=stale_work_cleanup removed=%s", removed)
        container.transcription_provider.load()
        await container.summary_provider.load()
        await container.job_service.start()
        await container.feishu_service.start()
        log_retention_task: asyncio.Task[None] | None = None
        if file_logging_enabled():
            log_retention_task = asyncio.create_task(
                run_log_retention_scheduler(),
                name="voxpull-log-retention",
            )
        logger.info("event=service_started")
        try:
            yield
        finally:
            logger.info("event=service_stopping")
            if log_retention_task is not None:
                log_retention_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await log_retention_task
            await container.feishu_service.stop()
            await container.job_service.stop()
            await container.summary_provider.aclose()
            await container.browser.close()
            await container.runner.close()
            logger.info("event=service_stopped")

    application = FastAPI(
        title="VoxPull",
        version="0.1.0",
        description="本地视频文案提取工具",
        lifespan=lifespan,
    )
    application.state.container = container

    @application.middleware("http")
    async def prevent_stale_web_assets(request: Request, call_next):
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    @application.exception_handler(VoxPullError)
    async def handle_voxpull_error(_request: Request, exc: VoxPullError) -> JSONResponse:
        body = ErrorResponse(code=exc.code, message=exc.message, retryable=exc.retryable)
        return JSONResponse(
            status_code=_HTTP_STATUS_BY_ERROR.get(exc.code, 500),
            content=body.model_dump(),
        )

    application.include_router(transcription.router)
    application.include_router(system.router)
    application.include_router(auth.router)
    application.include_router(jobs.router)
    application.include_router(summaries.router)
    application.include_router(batches.router)
    application.include_router(material_tags.router)
    application.include_router(material_search.router)
    application.include_router(feishu.router)
    application.mount("/static", StaticFiles(directory=settings.web_dir), name="static")

    @application.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(settings.web_dir / "index.html")

    return application


app = create_app()
