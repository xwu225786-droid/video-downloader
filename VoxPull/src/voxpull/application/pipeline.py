from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlparse

from voxpull.application.summary_service import SummaryService

from voxpull.domain.errors import InvalidInputError, UnsupportedUrlError, VoxPullError
from voxpull.domain.models import (
    DOUYIN_PUBLIC_SHARE_POLICY,
    DOUYIN_GUEST_POLICY,
    JobErrorInfo,
    JobResult,
    JobStage,
    JobStatus,
    MediaAssetInfo,
    MediaAssetKind,
    MediaInfo,
    MediaKind,
    SummaryStyle,
)
from voxpull.domain.naming import compact_media_id
from voxpull.domain.ports import (
    AudioExtractorPort,
    BrowserPort,
    CoverExtractorPort,
    DownloaderPort,
    JobRepositoryPort,
    StoragePort,
    TranscriberPort,
)


logger = logging.getLogger(__name__)
_URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
_TRAILING_PUNCTUATION = "。！？，,；;：:）)】]}>\"'"
_DIRECT_DOWNLOAD_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0 Safari/537.36"
)


def extract_url(content: str) -> str:
    content = content.strip()
    if not content or len(content) > 4096:
        raise InvalidInputError("分享内容不能为空且不能超过 4096 个字符")
    match = _URL_RE.search(content)
    if not match:
        raise InvalidInputError("分享内容中没有找到 URL")
    return validate_url(match.group(0).rstrip(_TRAILING_PUNCTUATION))


def extract_batch_urls(content: str) -> tuple[list[str], int]:
    if not content.strip() or len(content) > 100_000:
        raise InvalidInputError("请粘贴多个分享链接，内容不能超过 100000 个字符")
    urls = [validate_url(match.rstrip(_TRAILING_PUNCTUATION)) for match in _URL_RE.findall(content)]
    if not urls:
        raise InvalidInputError("没有找到可处理的 HTTP 或 HTTPS 链接")
    unique = list(dict.fromkeys(urls))
    if len(unique) > 200:
        raise InvalidInputError("每批最多处理 200 个不同链接，请分批提交")
    return unique, len(urls) - len(unique)


def validate_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as exc:
        raise InvalidInputError("链接格式无效") from exc
    if parsed.scheme not in {"http", "https"} or not host:
        raise InvalidInputError("只支持 HTTP 或 HTTPS 链接")
    if parsed.username or parsed.password or port not in {None, 80, 443}:
        raise UnsupportedUrlError("链接不能包含账号信息或非标准端口")
    return url


def is_douyin_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return (
        host == "douyin.com"
        or host.endswith(".douyin.com")
        or host == "iesdouyin.com"
        or host.endswith(".iesdouyin.com")
    )


def validate_douyin_url(url: str) -> str:
    url = validate_url(url)
    if not is_douyin_url(url):
        raise UnsupportedUrlError()
    return url


def extract_douyin_url(content: str) -> str:
    url = extract_url(content)
    if not is_douyin_url(url):
        raise UnsupportedUrlError()
    return url


class TranscriptionPipeline:
    def __init__(
        self,
        repository: JobRepositoryPort,
        browser: BrowserPort,
        downloader: DownloaderPort,
        audio_extractor: AudioExtractorPort,
        transcriber: TranscriberPort,
        storage: StoragePort,
        *,
        cover_extractor: CoverExtractorPort | None = None,
        download_concurrency: int = 5,
        ffmpeg_concurrency: int = 2,
        transcription_concurrency: int = 2,
    ) -> None:
        self.repository = repository
        self.browser = browser
        self.downloader = downloader
        self.audio_extractor = audio_extractor
        self.transcriber = transcriber
        self.storage = storage
        self.cover_extractor = cover_extractor
        self._download_slots = asyncio.Semaphore(max(1, download_concurrency))
        self._ffmpeg_slots = asyncio.Semaphore(max(1, ffmpeg_concurrency))
        self._transcription_slots = asyncio.Semaphore(max(1, transcription_concurrency))
        self._media_locks: dict[str, tuple[asyncio.Lock, int]] = {}
        self._media_locks_guard = asyncio.Lock()
        self._subtitle_states: dict[str, dict] = {}
        self.summary_service: SummaryService | None = None

    def subtitle_status(self, job_id: str) -> dict:
        job = self.repository.get(job_id)
        if job is None:
            raise InvalidInputError("任务不存在")
        state = self._subtitle_states.get(job_id)
        if job.result and job.result.transcript is not None and (not state or state["state"] == "completed"):
            return {"state": "completed", "progress": 100, "message": "字幕提取完成"}
        if state is None:
            return {"state": "idle", "progress": None, "message": "尚未提取字幕"}
        return {**{key: value for key, value in state.items() if key != "started"},
                "elapsed_seconds": int(time.monotonic() - state["started"])}

    def _subtitle_state(self, job_id: str, **changes) -> None:
        previous = self._subtitle_states.get(job_id, {"started": time.monotonic()})
        self._subtitle_states[job_id] = {**previous, **changes}
        logger.info("job_id=%s event=subtitle_progress state=%s progress=%s message=%s",
                    job_id, changes.get("state"), changes.get("progress"), changes.get("message"))

    async def extract_saved_transcript(self, job_id: str, *, regenerate: bool = False):
        """Add subtitles to an existing result without downloading or replacing its media."""
        async with self._media_lock(f"subtitle:{job_id}"):
            job = self.repository.get(job_id)
            if job is None or job.status is not JobStatus.COMPLETED or job.result is None:
                raise InvalidInputError("只能为已完成的作品提取字幕")
            if job.result.media.kind is not MediaKind.VIDEO:
                raise InvalidInputError("图文作品没有可提取的视频字幕")
            if job.result.transcript is not None and not regenerate:
                return job
            media = job.result.media
            video = Path(media.absolute_path)
            if not media.saved or not video.is_file():
                raise InvalidInputError("此作品没有保留本地视频，无法补提取字幕")
            work_id = f"subtitle-{uuid4().hex}"
            work = self.storage.create_work_dir(work_id)
            written = None
            self._subtitle_states[job_id] = {"started": time.monotonic()}
            self._subtitle_state(job_id, state="running", progress=None, message="等待提取音频")
            try:
                audio = work / "audio.wav"
                async with self._ffmpeg_slots:
                    self._subtitle_state(job_id, message="正在提取音频")
                    await self.audio_extractor.extract(video, audio)
                self._subtitle_state(job_id, message="等待语音识别")
                async with self._transcription_slots:
                    self._subtitle_state(job_id, message="正在识别语音", progress=None)
                    transcript = await self.transcriber.transcribe(
                        audio, job.language, work,
                        lambda value, message: self._subtitle_state(
                            job_id, state="running", progress=max(0, min(99, value)), message=message))
                self._subtitle_state(job_id, message="正在保存字幕")
                current = self.repository.get(job_id)
                if (current is None or current.result is None or not video.is_file()
                        or current.result.media.absolute_path != media.absolute_path):
                    raise InvalidInputError("原素材已变化，未保存本次字幕")
                # Never overwrite an existing hand-edited text file.
                for name in ("文案.txt", "字幕文案.txt", f"字幕文案-{uuid4().hex[:8]}.txt"):
                    candidate = video.parent / name
                    try:
                        handle = candidate.open("x", encoding="utf-8")
                    except FileExistsError:
                        continue
                    written = candidate
                    with handle:
                        handle.write(transcript.text)
                    break
                if written is None:
                    raise InvalidInputError("无法创建字幕文件，请重试")
                updated_media = replace(current.result.media, description_path=str(written))
                files = list(dict.fromkeys([*current.metadata.get("source_files", []), str(written)]))
                updated = self.repository.update(job_id, extract_txt=True,
                    result=replace(current.result, media=updated_media, transcript=transcript),
                    message="字幕提取完成", metadata={**current.metadata, "source_files": files})
                self._subtitle_state(job_id, state="completed", progress=100, message="字幕提取完成")
                return updated
            except BaseException as exc:
                if written is not None:
                    written.unlink(missing_ok=True)
                self._subtitle_state(job_id, state="failed", progress=None,
                                     message=exc.message if isinstance(exc, VoxPullError)
                                     else "字幕提取已中断，请重试")
                raise
            finally:
                self.storage.cleanup_work_dir(work_id)

    async def execute(self, job_id: str) -> None:
        job = self.repository.get(job_id)
        if job is None or job.status is not JobStatus.QUEUED:
            logger.warning("job_id=%s event=pipeline_skipped reason=job_missing", job_id)
            return
        started_at = time.monotonic()
        work_dir: Path | None = None
        logger.info(
            "job_id=%s event=pipeline_started language=%s save_video=%s",
            job_id,
            job.language,
            job.save_video,
        )
        self._update(
            job_id,
            status=JobStatus.RUNNING,
            stage=JobStage.ACQUIRING_COOKIE,
            progress=1,
            message="正在检查分享链接",
        )
        try:
            source_url = extract_url(job.content)
            work_dir = self.storage.create_work_dir(job_id)
            downloaded_video = None
            if is_douyin_url(source_url):
                logger.info("job_id=%s event=cookie_acquisition_started", job_id)
                def auth_state(state, message):
                    current = self.repository.get(job_id)
                    self._update(job_id, message=message, metadata={
                        **(current.metadata if current else {}), "auth_status": state,
                    })
                evidence = await self.browser.acquire(source_url, work_dir / "cookies.txt", on_state=auth_state)
                validate_douyin_url(evidence.final_url)
                download_url = evidence.final_url
                cookie_file = evidence.cookie_file
                user_agent = evidence.user_agent
                metadata = evidence.media
                downloaded_video = evidence.downloaded_video
                self._update(job_id, progress=10, message=(
                    ("已下载访客公开视频" if metadata and metadata.video_source_policy == DOUYIN_GUEST_POLICY
                     else "已下载公开分享页水印版") if downloaded_video else "已取得作品信息"
                ))
                logger.info(
                    "job_id=%s event=cookie_acquisition_completed metadata_available=%s",
                    job_id,
                    metadata is not None,
                )
            else:
                download_url = source_url
                cookie_file = work_dir / "cookies.txt"
                cookie_file.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
                user_agent = _DIRECT_DOWNLOAD_USER_AGENT
                metadata = None
                self._update(job_id, progress=10, message="链接有效，准备直接下载")
                logger.info("job_id=%s event=direct_source_validated", job_id)

            self._update(
                job_id,
                stage=JobStage.DOWNLOADING,
                progress=11,
                message="正在识别作品类型",
            )
            if metadata is None:
                logger.info("job_id=%s event=media_probe_started", job_id)
                async with self._download_slots:
                    metadata = await self.downloader.probe(download_url, cookie_file, user_agent)
            logger.info(
                "job_id=%s event=media_identified media_id=%s media_kind=%s",
                job_id,
                metadata.id,
                metadata.kind.value,
            )
            current = self.repository.get(job_id)
            self._update(job_id, metadata={**(current.metadata if current else {}), "title": metadata.title})

            if metadata.kind is MediaKind.IMAGES:
                async with self._media_lock(f"images:{metadata.id}"):
                    image_folder = self.storage.find_image_folder(
                        metadata.id,
                        source_policy=metadata.image_source_policy,
                    )
                    if image_folder is None:
                        self._update(job_id, message="等待图片下载资源")
                        logger.info(
                            "job_id=%s event=image_download_started media_id=%s",
                            job_id,
                            metadata.id,
                        )
                        async with self._download_slots:
                            downloaded_folder = await self.downloader.download_images(
                                download_url,
                                metadata,
                                cookie_file,
                                user_agent,
                                work_dir,
                                lambda value, message: self._scaled_progress(
                                    job_id, value, 12, 95, message
                                ),
                            )
                        self.storage.prepare_material(metadata.id, metadata.title, "images")
                        image_folder = self.storage.publish_image_folder(
                            downloaded_folder,
                            metadata.id,
                        )
                        logger.info(
                            "job_id=%s event=image_download_completed media_id=%s",
                            job_id,
                            metadata.id,
                        )
                    else:
                        target_folder = self.storage.prepare_material(metadata.id, metadata.title, "images")
                        if target_folder != image_folder:
                            image_folder = self.storage.publish_image_folder(image_folder, metadata.id)
                        self._update(job_id, progress=95, message="已复用本地图片文件夹")
                        logger.info(
                            "job_id=%s event=image_reused media_id=%s",
                            job_id,
                            metadata.id,
                        )

                    cover_path = self.storage.name_gallery_files(image_folder)
                    title_path, description_path = self.storage.save_material_text(
                        metadata.id, metadata.title, "images", description=metadata.description,
                    )
                    self._record_source_files(job_id, title_path, *([description_path] if description_path else []),
                                              *([cover_path] if cover_path else []), image_folder / "manifest.json")
                    assets = _gallery_asset_infos(image_folder)
                    self._record_source_files(job_id, *(Path(asset.absolute_path) for asset in assets))
                image_count = sum(asset.kind is MediaAssetKind.IMAGE for asset in assets)
                live_count = sum(asset.kind is MediaAssetKind.LIVE_MOTION for asset in assets)
                result = JobResult(
                    media=MediaInfo(
                        id=metadata.id,
                        title=metadata.title,
                        kind=MediaKind.IMAGES,
                        filename=image_folder.name,
                        absolute_path=str(image_folder.resolve()),
                        saved=True,
                        asset_count=image_count,
                        live_photo_count=live_count,
                        published_at=metadata.published_at,
                        assets=assets,
                        title_path=str(title_path.resolve()),
                        cover_path=str(cover_path.resolve()) if cover_path else None,
                        description=metadata.description,
                        description_path=str(description_path.resolve()) if description_path else None,
                    )
                )
                summary = (
                    f"{image_count} 张图片已保存"
                    if live_count == 0
                    else f"{image_count} 张图片已保存，其中 {live_count} 张为 Live 图"
                )
                self._update(job_id, result=result)
                await self._maybe_generate_summary(job_id, metadata.description)
                self._update(
                    job_id,
                    status=JobStatus.COMPLETED,
                    stage=JobStage.COMPLETED,
                    progress=100,
                    message=summary,
                    result=result,
                )
                logger.info(
                    "job_id=%s event=pipeline_completed media_kind=images image_count=%s "
                    "live_count=%s duration_seconds=%.2f",
                    job_id,
                    image_count,
                    live_count,
                    time.monotonic() - started_at,
                )
                return

            # Temporary videos stay in the job directory and are removed by the
            # existing work-directory cleanup after transcription. Only look in
            # or publish to persistent storage when the user opted to keep MP4s.
            video_storage_id = (
                f"{metadata.id}_{metadata.video_source_policy}"
                if metadata.video_source_policy else metadata.id
            )
            material_folder = self.storage.prepare_material(video_storage_id, metadata.title, "video")
            if job.save_video:
                async with self._media_lock(f"video:{video_storage_id}"):
                    video_path = self.storage.find_video(video_storage_id)
                    if video_path is not None:
                        self._update(job_id, progress=45, message="已复用本地 MP4")
                        logger.info(
                            "job_id=%s event=video_reused media_id=%s",
                            job_id,
                            metadata.id,
                        )
                    elif downloaded_video is not None:
                        video_path = self.storage.publish_video(downloaded_video, video_storage_id)
                        self._update(job_id, progress=45, message=(
                            "已保存访客公开视频" if metadata.video_source_policy == DOUYIN_GUEST_POLICY
                            else "已保存公开分享页水印版"
                        ))
                    else:
                        self._update(job_id, message="等待视频下载资源")
                        logger.info(
                            "job_id=%s event=video_download_started media_id=%s saved=true",
                            job_id,
                            metadata.id,
                        )
                        async with self._download_slots:
                            downloaded = await self.downloader.download(
                                download_url,
                                metadata,
                                cookie_file,
                                user_agent,
                                work_dir,
                                lambda value, message: self._scaled_progress(
                                    job_id, value, 12, 45, message
                                ),
                            )
                        video_path = self.storage.publish_video(downloaded, video_storage_id)
                        logger.info(
                            "job_id=%s event=video_download_completed media_id=%s saved=true",
                            job_id,
                            metadata.id,
                        )
            elif downloaded_video is not None:
                video_path = downloaded_video
            else:
                self._update(job_id, message="等待视频下载资源")
                logger.info(
                    "job_id=%s event=video_download_started media_id=%s saved=false",
                    job_id,
                    metadata.id,
                )
                async with self._download_slots:
                    video_path = await self.downloader.download(
                        download_url,
                        metadata,
                        cookie_file,
                        user_agent,
                        work_dir,
                        lambda value, message: self._scaled_progress(
                            job_id, value, 12, 45, message
                        ),
                    )
                video_path = _compact_temporary_video_path(video_path, metadata.id)
                logger.info(
                    "job_id=%s event=video_download_completed media_id=%s saved=false",
                    job_id,
                    metadata.id,
                )

            if job.save_video:
                self._record_source_files(job_id, video_path)
            saved_title, saved_text = self.storage.save_material_text(
                video_storage_id, metadata.title, "video", description=metadata.description)
            self._record_source_files(job_id, saved_title, *([saved_text] if saved_text else []))
            # Temporary files can be previewed while processing without changing retention.
            self._update(job_id, progress=45, message="视频已下载，正在准备字幕", result=JobResult(
                media=MediaInfo(id=metadata.id, title=metadata.title, kind=MediaKind.VIDEO,
                    filename=video_path.name, absolute_path=str(video_path.resolve()), saved=job.save_video,
                    duration=metadata.duration, published_at=metadata.published_at, asset_count=1,
                    title_path=str(saved_title.resolve()), description=metadata.description,
                    description_path=str(saved_text.resolve()) if saved_text else None,
                    video_source_policy=metadata.video_source_policy)))
            cover_path: Path | None = None
            title_path: Path | None = None
            if self.cover_extractor is not None:
                self._update(job_id, progress=46, message="正在提取视频第一帧和标题")
                async with self._media_lock(f"details:{video_storage_id}"):
                    async with self._ffmpeg_slots:
                        extracted_cover = work_dir / "cover.jpg"
                        await self.cover_extractor.extract(video_path, extracted_cover)
                    cover_path, title_path = self.storage.publish_video_details(
                        extracted_cover, metadata.title, video_storage_id
                    )
                    self._record_source_files(job_id, cover_path, title_path)
                logger.info("job_id=%s event=video_details_saved media_id=%s", job_id, metadata.id)
                current = self.repository.get(job_id)
                if current and current.result:
                    self._update(job_id, result=replace(current.result, media=replace(current.result.media,
                        cover_path=str(cover_path.resolve()), title_path=str(title_path.resolve()))))

            transcript = None
            if job.extract_txt:
                self._update(
                    job_id,
                    stage=JobStage.EXTRACTING_AUDIO,
                    progress=46,
                    message="等待音频提取资源",
                )
                audio_path = work_dir / "audio.wav"
                async with self._ffmpeg_slots:
                    self._update(job_id, message="正在提取 16 kHz 单声道音频")
                    logger.info("job_id=%s event=audio_extraction_started", job_id)
                    await self.audio_extractor.extract(video_path, audio_path)
                self._update(job_id, progress=55, message="音频提取完成")
                logger.info("job_id=%s event=audio_extraction_completed", job_id)

                self._update(
                    job_id,
                    stage=JobStage.TRANSCRIBING,
                    progress=56,
                    message="等待语音识别资源",
                )
                async with self._transcription_slots:
                    self._update(job_id, message="正在识别语音")
                    logger.info(
                        "job_id=%s event=transcription_started language=%s",
                        job_id,
                        job.language,
                    )
                    transcript = await self.transcriber.transcribe(
                        audio_path,
                        job.language,
                        work_dir,
                        lambda value, message: self._scaled_progress(job_id, value, 56, 99, message),
                    )
                logger.info(
                    "job_id=%s event=transcription_completed detected_language=%s segments=%s",
                    job_id,
                    transcript.detected_language,
                    len(transcript.segments),
                )
            saved_title, text_path = self.storage.save_material_text(
                video_storage_id, metadata.title, "video", description=metadata.description,
                transcript=transcript.text if transcript is not None else None,
            )
            title_path = saved_title
            self._record_source_files(job_id, saved_title, *([text_path] if text_path else []))
            caption_path = material_folder / "作品文案.txt"
            if caption_path.is_file():
                self._record_source_files(job_id, caption_path)
            result = JobResult(
                media=MediaInfo(
                    id=metadata.id,
                    title=metadata.title,
                    kind=MediaKind.VIDEO,
                    filename=video_path.name if job.save_video else "视频.mp4",
                    absolute_path=str((video_path if job.save_video else
                                       material_folder / "视频.mp4").resolve()),
                    saved=job.save_video,
                    duration=metadata.duration,
                    published_at=metadata.published_at,
                    asset_count=1,
                    cover_path=str(cover_path.resolve()) if cover_path else None,
                    title_path=str(title_path.resolve()) if title_path else None,
                    description_path=str(text_path.resolve()) if text_path else None,
                    video_source_policy=metadata.video_source_policy,
                ),
                transcript=transcript,
            )
            completion_message = "文案提取完成" if job.extract_txt else "视频处理完成"
            if metadata.video_source_policy == DOUYIN_PUBLIC_SHARE_POLICY:
                completion_message += " · 公开分享页水印版"
            elif metadata.video_source_policy == DOUYIN_GUEST_POLICY:
                completion_message += " · 访客公开资源"
            self._update(job_id, result=result if job.save_video else replace(result,
                media=replace(result.media, absolute_path=str(video_path.resolve()))))
            await self._maybe_generate_summary(job_id, transcript.text if transcript is not None else "")
            current = self.repository.get(job_id)
            if current and current.metadata.get("summary_state") == "failed":
                completion_message += " · AI总结未完成，可单独重试"
            self._update(
                job_id,
                status=JobStatus.COMPLETED,
                stage=JobStage.COMPLETED,
                progress=100,
                message=completion_message,
                result=result,
            )
            logger.info(
                "job_id=%s event=pipeline_completed media_kind=video duration_seconds=%.2f",
                job_id,
                time.monotonic() - started_at,
            )
        except VoxPullError as exc:
            current = self.repository.get(job_id)
            logger.warning(
                "job_id=%s event=pipeline_failed stage=%s code=%s retryable=%s "
                "duration_seconds=%.2f detail=%s",
                job_id,
                current.stage.value if current is not None else "unknown",
                exc.code,
                exc.retryable,
                time.monotonic() - started_at,
                exc.detail or exc.message,
            )
            self._mark_failed(job_id, exc.code, exc.message, exc.retryable)
        except Exception:
            current = self.repository.get(job_id)
            logger.exception(
                "job_id=%s event=pipeline_failed stage=%s code=internal_error "
                "duration_seconds=%.2f",
                job_id,
                current.stage.value if current is not None else "unknown",
                time.monotonic() - started_at,
            )
            self._mark_failed(job_id, "internal_error", "发生内部错误，请查看本地日志", False)
        finally:
            if work_dir is not None:
                self.storage.cleanup_work_dir(job_id)
                logger.debug("job_id=%s event=work_directory_cleaned", job_id)

    @asynccontextmanager
    async def _media_lock(self, key: str) -> AsyncIterator[None]:
        async with self._media_locks_guard:
            lock, references = self._media_locks.get(key, (asyncio.Lock(), 0))
            self._media_locks[key] = (lock, references + 1)
        try:
            async with lock:
                yield
        finally:
            async with self._media_locks_guard:
                current_lock, references = self._media_locks[key]
                if references == 1:
                    del self._media_locks[key]
                else:
                    self._media_locks[key] = (current_lock, references - 1)

    async def _maybe_generate_summary(self, job_id: str, text: str) -> None:
        job = self.repository.get(job_id)
        if not job or not job.metadata.get("auto_summary"):
            return
        self._update(job_id, progress=99, message="文案已就绪，正在生成AI总结")
        try:
            if self.summary_service is None:
                raise InvalidInputError("AI总结服务未配置")
            await self.summary_service.summarize(job_id, text, SummaryStyle.BRIEF)
        except Exception:
            current = self.repository.get(job_id)
            if current:
                self._update(job_id, metadata={**current.metadata, "summary_state": "failed"})
            logger.warning("job_id=%s event=automatic_summary_failed", job_id, exc_info=True)

    def _scaled_progress(self, job_id: str, value: int, start: int, end: int, message: str) -> None:
        scaled = start + int(max(0, min(100, value)) * (end - start) / 100)
        self._update(job_id, progress=scaled, message=message)

    def _record_source_files(self, job_id: str, *paths: Path) -> None:
        job = self.repository.get(job_id)
        if job is not None:
            files = list(dict.fromkeys([*job.metadata.get("source_files", []),
                                        *(str(path.resolve()) for path in paths)]))
            self._update(job_id, metadata={**job.metadata, "source_files": files})

    def _update(self, job_id: str, **changes: object) -> None:
        current = self.repository.get(job_id)
        if current is not None and current.status not in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PAUSED}:
            self.repository.update(job_id, **changes)

    def _mark_failed(self, job_id: str, code: str, message: str, retryable: bool) -> None:
        self._update(
            job_id,
            status=JobStatus.FAILED,
            stage=JobStage.FAILED,
            message=message,
            error=JobErrorInfo(code=code, message=message, retryable=retryable),
        )


def _gallery_asset_infos(folder: Path) -> tuple[MediaAssetInfo, ...]:
    assets: list[MediaAssetInfo] = []
    for path in sorted(folder.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.name == "manifest.json" or path.name.startswith("."):
            continue
        match = re.fullmatch(r"(图片|视频)(\d+)\.[^.]+", path.name)
        prefix = path.name.split(".", 1)[0]
        if match:
            index = int(match[2])
            kind = MediaAssetKind.LIVE_MOTION if match[1] == "视频" else MediaAssetKind.IMAGE
        elif prefix.isdigit():
            index = int(prefix)
            kind = MediaAssetKind.LIVE_MOTION if ".live." in path.name else MediaAssetKind.IMAGE
        else:
            continue
        assets.append(
            MediaAssetInfo(
                index=index,
                kind=kind,
                filename=path.name,
                absolute_path=str(path.resolve()),
            )
        )
    return tuple(assets)


def _compact_temporary_video_path(path: Path, media_id: str) -> Path:
    destination = path.with_name(f"{compact_media_id(media_id)}.mp4")
    if path == destination:
        return path
    return path.replace(destination)
