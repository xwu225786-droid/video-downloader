from __future__ import annotations

import asyncio
import contextlib
import http.cookiejar
import json
import logging
import os
import threading
import time
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urljoin, urlparse

import httpx

from voxpull.domain.errors import (
    CookieRefreshRequiredError,
    CookieCheckRequiredError,
    PlatformVerificationRequiredError,
    PlatformAccessRestrictedError,
    DownloadFailedError,
    TaskTimeoutError,
    VoxPullError,
)
from voxpull.domain.models import BrowserEvidence, ImageAssetMetadata, MediaKind, MediaMetadata
from voxpull.domain.naming import compact_media_id
from voxpull.domain.ports import ProgressCallback
from voxpull.infrastructure.browser import _MOBILE_SHARE_USER_AGENT, _metadata_from_mobile_share_html, _video_id_from_url
from voxpull.infrastructure.publication import publication_timestamp


logger = logging.getLogger(__name__)
_XIAOHONGSHU_MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 "
    "Mobile/15E148 Safari/604.1"
)
_XIAOHONGSHU_IMAGE_SOURCE_POLICY = "xiaohongshu-original-png-v3"
_DOUYIN_SHARE_HOSTS = ("douyin.com", "iesdouyin.com")
_DOUYIN_SHARE_MEDIA_HOSTS = (*_DOUYIN_SHARE_HOSTS, "douyinvod.com", "douyinstatic.com", "bytecdn.cn", "bytecdn.com", "byteimg.com")
_THREAD_CANCEL: ContextVar[threading.Event | None] = ContextVar("download_cancel", default=None)


class _DownloadCancelled(BaseException):
    """Leave yt-dlp without treating a user interruption as a retryable error."""


def _check_download_cancelled() -> None:
    event = _THREAD_CANCEL.get()
    if event is not None and event.is_set():
        raise _DownloadCancelled()


async def _run_download_thread(function, *args):
    event = threading.Event()
    token = _THREAD_CANCEL.set(event)
    try:
        task = asyncio.create_task(asyncio.to_thread(function, *args))
    finally:
        _THREAD_CANCEL.reset(token)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        event.set()
        # Join before the pipeline removes its workspace. Network I/O exits at
        # the next yt-dlp hook/log or socket timeout; no orphan keeps writing.
        try:
            await asyncio.shield(task)
        except (_DownloadCancelled, Exception):
            pass
        raise


@asynccontextmanager
async def _public_share_response(client: httpx.AsyncClient, url: str, hosts: tuple[str, ...]):
    for _ in range(6):
        host = (urlparse(url).hostname or "").lower()
        if not _is_safe_media_url(url) or not any(host == base or host.endswith("." + base) for base in hosts):
            raise DownloadFailedError("公开分享页返回了不受支持的地址")
        request = client.build_request("GET", url)
        request.headers.pop("cookie", None)
        response = await client.send(request, stream=True, follow_redirects=False)
        try:
            if response.has_redirect_location:
                url = urljoin(url, response.headers["location"])
                continue
            response.raise_for_status()
            yield response
            return
        finally:
            await response.aclose()
    raise DownloadFailedError("公开分享页跳转次数过多")


@dataclass(frozen=True, slots=True)
class _DownloadedFile:
    path: Path
    byte_count: int


class _YtdlpLogger:
    def debug(self, message: str) -> None:
        _check_download_cancelled()
        logger.debug("yt-dlp: %s", message)

    def warning(self, message: str) -> None:
        _check_download_cancelled()
        logger.warning("yt-dlp: %s", message)

    def error(self, message: str) -> None:
        _check_download_cancelled()
        logger.error("yt-dlp: %s", message)


class YtDlpDownloader:
    def __init__(
        self,
        timeout: float,
        image_concurrency: int = 5,
        *,
        image_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.timeout = timeout
        self.image_concurrency = max(1, image_concurrency)
        self._image_slots = asyncio.Semaphore(self.image_concurrency)
        self._image_conversion_slots = asyncio.Semaphore(min(2, self.image_concurrency))
        self._image_transport = image_transport

    async def download_public_douyin_share(self, url: str, cookie_file: Path) -> BrowserEvidence | None:
        """Try an anonymously accessible, platform-provided copy in the job workspace."""
        temporary = cookie_file.parent / "douyin-share.part"
        destination = temporary.with_suffix(".mp4")
        timeout = min(self.timeout, 45)
        try:
            async with asyncio.timeout(timeout), httpx.AsyncClient(
                timeout=min(timeout, 12), trust_env=False, headers={"User-Agent": _MOBILE_SHARE_USER_AGENT},
            ) as client:
                video_id = _video_id_from_url(url)
                if video_id is None and urlparse(url).hostname == "v.douyin.com":
                    async with _public_share_response(client, url, _DOUYIN_SHARE_HOSTS) as response:
                        video_id = _video_id_from_url(str(response.url))
                if video_id is None:
                    return None
                share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"
                async with _public_share_response(client, share_url, _DOUYIN_SHARE_HOSTS) as response:
                    html = bytearray()
                    async for chunk in response.aiter_bytes(64 * 1024):
                        html.extend(chunk)
                        if len(html) > 4 * 1024 * 1024:
                            return None
                metadata = _metadata_from_mobile_share_html(
                    html.decode("utf-8", errors="replace"), video_id, public_watermarked=True,
                )
                if metadata is None:
                    return None
                client.headers["Referer"] = share_url
                async with _public_share_response(client, metadata.source_urls[0], _DOUYIN_SHARE_MEDIA_HOSTS) as response:
                    chunks = response.aiter_bytes(256 * 1024)
                    first = await anext(chunks, b"")
                    if not _looks_like_mp4(first):
                        return None
                    await _write_response_body_async(chunks, temporary, first, time.monotonic() + timeout)
                os.replace(temporary, destination)
                return BrowserEvidence(share_url, _MOBILE_SHARE_USER_AGENT, cookie_file, metadata, destination)
        except (TimeoutError, httpx.HTTPError, VoxPullError, ValueError):
            logger.info("Public Douyin share copy unavailable")
            return None
        finally:
            temporary.unlink(missing_ok=True)

    async def probe(self, url: str, cookie_file: Path, user_agent: str) -> MediaMetadata:
        try:
            async with asyncio.timeout(self.timeout):
                return await _run_download_thread(self._probe_sync, url, cookie_file, user_agent)
        except TimeoutError as exc:
            raise TaskTimeoutError("读取作品信息超时") from exc
        except Exception as exc:
            raise _translate_download_error(exc, url) from exc

    async def download(
        self,
        url: str,
        metadata: MediaMetadata,
        cookie_file: Path,
        user_agent: str,
        work_dir: Path,
        progress: ProgressCallback,
    ) -> Path:
        deadline = time.monotonic() + self.timeout
        try:
            async with asyncio.timeout(self.timeout + 5):
                return await _run_download_thread(
                    self._download_sync,
                    url,
                    metadata,
                    cookie_file,
                    user_agent,
                    work_dir,
                    progress,
                    deadline,
                )
        except TimeoutError as exc:
            raise TaskTimeoutError("视频下载超时") from exc
        except Exception as exc:
            if isinstance(exc, (TaskTimeoutError, CookieRefreshRequiredError, DownloadFailedError)):
                raise
            raise _translate_download_error(exc, url) from exc

    async def download_images(
        self,
        url: str,
        metadata: MediaMetadata,
        cookie_file: Path,
        user_agent: str,
        work_dir: Path,
        progress: ProgressCallback,
    ) -> Path:
        deadline = time.monotonic() + self.timeout
        try:
            async with asyncio.timeout(self.timeout + 5):
                return await self._download_images_async(
                    url,
                    metadata,
                    cookie_file,
                    user_agent,
                    work_dir,
                    progress,
                    deadline,
                )
        except TimeoutError as exc:
            raise TaskTimeoutError("图片下载超时") from exc
        except Exception as exc:
            if isinstance(exc, (TaskTimeoutError, CookieRefreshRequiredError, DownloadFailedError)):
                raise
            raise _translate_download_error(exc, url) from exc

    @staticmethod
    def _base_options(cookie_file: Path, user_agent: str, source_url: str) -> dict[str, Any]:
        headers = {"User-Agent": user_agent}
        if _is_douyin_url(source_url):
            headers["Referer"] = "https://www.douyin.com/"
        elif _is_xiaohongshu_url(source_url):
            headers["Referer"] = "https://www.xiaohongshu.com/"
        return {
            "cookiefile": str(cookie_file),
            "http_headers": headers,
            "noplaylist": True,
            "logger": _YtdlpLogger(),
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "retries": 3,
        }

    def _probe_sync(self, url: str, cookie_file: Path, user_agent: str) -> MediaMetadata:
        import yt_dlp

        _check_download_cancelled()

        if _is_xiaohongshu_url(url):
            if (urlparse(url).hostname or "").endswith(("xhslink.com", "xhslink.cn")):
                with httpx.Client(follow_redirects=True, timeout=min(self.timeout, 30)) as client:
                    response = client.get(url, headers={"User-Agent": _XIAOHONGSHU_MOBILE_USER_AGENT})
                    url = str(response.url)
            url = _normalize_xiaohongshu_url(url)
        options = self._base_options(cookie_file, user_agent, url)
        if _is_xiaohongshu_url(url):
            mobile_metadata = self._probe_xiaohongshu_images(yt_dlp, options, url)
            if mobile_metadata is not None:
                return mobile_metadata
        options["skip_download"] = True
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        _check_download_cancelled()
        if not isinstance(info, dict) or not info.get("id"):
            raise DownloadFailedError("无法读取作品信息")
        return MediaMetadata(
            id=str(info["id"]),
            title=str(info.get("title") or info["id"]),
            kind=MediaKind.VIDEO,
            duration=float(info["duration"]) if info.get("duration") is not None else None,
            published_at=publication_timestamp(info.get("timestamp")),
        )

    @staticmethod
    def _probe_xiaohongshu_images(
        yt_dlp: Any,
        options: dict[str, Any],
        url: str,
    ) -> MediaMetadata | None:
        from yt_dlp.extractor.xiaohongshu import XiaoHongShuIE
        from yt_dlp.utils import js_to_json

        request_options = _xiaohongshu_mobile_options(options)
        with yt_dlp.YoutubeDL(request_options) as ydl:
            extractor = XiaoHongShuIE(ydl)
            try:
                media_id = extractor._match_id(url)
            except Exception:
                return None
            webpage = extractor._download_webpage(url, media_id)
            initial_state = extractor._search_json(
                r"window\.__INITIAL_STATE__\s*=",
                webpage,
                "initial state",
                media_id,
                transform_source=js_to_json,
            )
        note_info = _xiaohongshu_note_from_initial_state(initial_state, media_id)
        return (_metadata_from_xiaohongshu_video(note_info, media_id)
                or _metadata_from_xiaohongshu_note(note_info, media_id))

    def _download_sync(
        self,
        url: str,
        metadata: MediaMetadata,
        cookie_file: Path,
        user_agent: str,
        work_dir: Path,
        progress: ProgressCallback,
        deadline: float,
    ) -> Path:
        import yt_dlp

        def hook(data: dict[str, Any]) -> None:
            _check_download_cancelled()
            if time.monotonic() > deadline:
                raise TaskTimeoutError("视频下载超时")
            if data.get("status") == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                downloaded = data.get("downloaded_bytes", 0)
                percent = int(downloaded * 100 / total) if total else 0
                progress(max(0, min(99, percent)), "正在下载 MP4")
            elif data.get("status") == "finished":
                progress(100, "MP4 下载完成")

        filename_stem = compact_media_id(metadata.id)
        _check_download_cancelled()
        options = self._download_options(
            cookie_file, user_agent, url, work_dir, filename_stem, hook
        )
        if _is_xiaohongshu_url(url):
            options = _xiaohongshu_mobile_options(options)
        if metadata.source_urls:
            prepared = self._download_direct_video(
                yt_dlp, options, metadata, user_agent, work_dir, filename_stem
            )
        else:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                prepared = Path(ydl.prepare_filename(info))
        candidates = [
            work_dir / f"{filename_stem}.mp4",
            prepared.with_suffix(".mp4"),
            prepared,
        ]
        for candidate in candidates:
            _check_download_cancelled()
            if candidate.is_file() and candidate.stat().st_size > 0:
                if candidate.suffix.lower() != ".mp4":
                    raise DownloadFailedError("yt-dlp 未能生成 MP4 文件")
                return candidate
        raise DownloadFailedError("yt-dlp 未生成可用的 MP4 文件")

    async def _download_images_async(
        self,
        source_url: str,
        metadata: MediaMetadata,
        cookie_file: Path,
        user_agent: str,
        work_dir: Path,
        progress: ProgressCallback,
        deadline: float,
    ) -> Path:
        if metadata.kind is not MediaKind.IMAGES or not metadata.images:
            raise DownloadFailedError("作品中没有可下载的图片")

        gallery_dir = work_dir / "images"
        gallery_dir.mkdir(parents=True, exist_ok=False)
        cookie_jar = http.cookiejar.MozillaCookieJar(str(cookie_file))
        if cookie_file.is_file():
            with contextlib.suppress(OSError, http.cookiejar.LoadError):
                cookie_jar.load(ignore_discard=True, ignore_expires=True)
        referer = (
            "https://www.douyin.com/"
            if _is_douyin_url(source_url)
            else "https://www.xiaohongshu.com/"
        )
        headers = {
            "User-Agent": user_agent,
            "Referer": referer,
            "Accept": "image/avif,image/webp,image/apng,image/*,video/mp4,*/*;q=0.8",
        }
        total_files = sum(1 + int(asset.is_live) for asset in metadata.images)
        completed = 0
        started_at = time.monotonic()
        image_tasks: dict[int, asyncio.Task[_DownloadedFile]] = {}
        motion_tasks: dict[int, asyncio.Task[_DownloadedFile]] = {}
        all_tasks: list[asyncio.Task[_DownloadedFile]] = []

        async def track(
            download: Awaitable[_DownloadedFile],
            asset: ImageAssetMetadata,
            media_label: str,
        ) -> _DownloadedFile:
            nonlocal completed
            downloaded = await download
            completed += 1
            progress(
                int(completed * 100 / total_files),
                f"已保存 {completed}/{total_files} 个文件（{media_label} {asset.index}）",
            )
            return downloaded

        limits = httpx.Limits(
            max_connections=self.image_concurrency,
            max_keepalive_connections=self.image_concurrency,
        )
        async with httpx.AsyncClient(
            headers=headers,
            cookies=cookie_jar,
            follow_redirects=True,
            timeout=httpx.Timeout(30),
            limits=limits,
            transport=self._image_transport,
        ) as client:
            for asset in metadata.images:
                image_task = asyncio.create_task(
                    track(
                        self._download_image_candidate(
                            client,
                            asset.source_urls,
                            gallery_dir,
                            f"{asset.index:03d}",
                            deadline,
                        ),
                        asset,
                        "图片",
                    )
                )
                image_tasks[asset.index] = image_task
                all_tasks.append(image_task)
                if asset.motion_urls:
                    motion_task = asyncio.create_task(
                        track(
                            self._download_motion_candidate(
                                client,
                                asset.motion_urls,
                                gallery_dir / f"{asset.index:03d}.live.mp4",
                                deadline,
                            ),
                            asset,
                            "Live",
                        )
                    )
                    motion_tasks[asset.index] = motion_task
                    all_tasks.append(motion_task)

            try:
                await asyncio.gather(*all_tasks)
            except BaseException:
                for task in all_tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*all_tasks, return_exceptions=True)
                raise

        manifest_assets = [
            {
                "index": asset.index,
                "image": image_tasks[asset.index].result().path.name,
                "motion": (
                    motion_tasks[asset.index].result().path.name
                    if asset.index in motion_tasks
                    else None
                ),
                "width": asset.width,
                "height": asset.height,
            }
            for asset in metadata.images
        ]

        (gallery_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "id": metadata.id,
                    "title": metadata.title,
                    "kind": metadata.kind.value,
                    "image_source_policy": metadata.image_source_policy,
                    "description": metadata.description,
                    "assets": manifest_assets,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        total_bytes = sum(task.result().byte_count for task in all_tasks)
        logger.info(
            "event=image_gallery_download_completed media_id=%s file_count=%s "
            "bytes=%s duration_seconds=%.2f",
            metadata.id,
            total_files,
            total_bytes,
            time.monotonic() - started_at,
        )
        return gallery_dir

    async def _download_image_candidate(
        self,
        client: httpx.AsyncClient,
        urls: tuple[str, ...],
        directory: Path,
        stem: str,
        deadline: float,
    ) -> _DownloadedFile:
        last_error: Exception | None = None
        for candidate_index, media_url in enumerate(urls, start=1):
            temporary = directory / f".{stem}.part"
            converted_temporary = directory / f".{stem}.png.part"
            try:
                async with self._image_slots:
                    async with client.stream("GET", media_url) as response:
                        response.raise_for_status()
                        final_url = str(response.url)
                        if not _is_safe_media_url(final_url):
                            raise DownloadFailedError("图片地址不安全")
                        chunks = response.aiter_bytes(chunk_size=256 * 1024)
                        first_chunk = await anext(chunks, b"")
                        extension = _image_extension(
                            _content_type(response),
                            final_url,
                            first_chunk,
                        )
                        if extension is None:
                            raise DownloadFailedError("服务器没有返回有效图片")
                        await _write_response_body_async(
                            chunks,
                            temporary,
                            first_chunk,
                            deadline,
                        )
                if extension in {"heic", "heif"}:
                    destination = directory / f"{stem}.png"
                    async with self._image_conversion_slots:
                        byte_count = await _run_download_thread(
                            _convert_heif_to_png,
                            temporary,
                            converted_temporary,
                            destination,
                        )
                    temporary.unlink(missing_ok=True)
                else:
                    destination = directory / f"{stem}.{extension}"
                    os.replace(temporary, destination)
                    byte_count = destination.stat().st_size
                return _DownloadedFile(destination, byte_count)
            except asyncio.CancelledError, TaskTimeoutError:
                temporary.unlink(missing_ok=True)
                converted_temporary.unlink(missing_ok=True)
                raise
            except Exception as exc:
                last_error = exc
                temporary.unlink(missing_ok=True)
                converted_temporary.unlink(missing_ok=True)
                logger.warning(
                    "Image candidate failed: stem=%s candidate=%s/%s host=%s error=%s",
                    stem,
                    candidate_index,
                    len(urls),
                    urlparse(media_url).hostname or "unknown",
                    exc,
                )
        raise DownloadFailedError(
            f"图片 {stem} 下载失败",
            detail=str(last_error) if last_error else None,
        )

    async def _download_motion_candidate(
        self,
        client: httpx.AsyncClient,
        urls: tuple[str, ...],
        destination: Path,
        deadline: float,
    ) -> _DownloadedFile:
        last_error: Exception | None = None
        temporary = destination.with_suffix(".part")
        for media_url in urls:
            try:
                async with self._image_slots:
                    async with client.stream("GET", media_url) as response:
                        response.raise_for_status()
                        final_url = str(response.url)
                        if not _is_safe_media_url(final_url):
                            raise DownloadFailedError("Live 图动态地址不安全")
                        chunks = response.aiter_bytes(chunk_size=256 * 1024)
                        first_chunk = await anext(chunks, b"")
                        content_type = _content_type(response)
                        if not (content_type.startswith("video/") or _looks_like_mp4(first_chunk)):
                            raise DownloadFailedError("服务器没有返回有效的 Live 图动态文件")
                        byte_count = await _write_response_body_async(
                            chunks,
                            temporary,
                            first_chunk,
                            deadline,
                        )
                        os.replace(temporary, destination)
                        return _DownloadedFile(destination, byte_count)
            except asyncio.CancelledError, TaskTimeoutError:
                temporary.unlink(missing_ok=True)
                raise
            except Exception as exc:
                last_error = exc
                temporary.unlink(missing_ok=True)
        raise DownloadFailedError(
            f"Live 图 {destination.stem} 下载失败",
            detail=str(last_error) if last_error else None,
        )

    def _download_options(
        self,
        cookie_file: Path,
        user_agent: str,
        source_url: str,
        work_dir: Path,
        video_id: str,
        hook: Any,
    ) -> dict[str, Any]:
        options = self._base_options(cookie_file, user_agent, source_url)
        options.update(
            {
                "format": "bv*+ba/b",
                "merge_output_format": "mp4",
                "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}],
                "outtmpl": str(work_dir / f"{video_id}.%(ext)s"),
                "progress_hooks": [hook],
                "postprocessor_hooks": [lambda _: _check_download_cancelled()],
                "overwrites": True,
            }
        )
        return options

    @staticmethod
    def _download_direct_video(
        yt_dlp: Any,
        options: dict[str, Any],
        metadata: MediaMetadata,
        user_agent: str,
        work_dir: Path,
        filename_stem: str,
    ) -> Path:
        last_error: Exception | None = None
        for index, media_url in enumerate(metadata.source_urls, start=1):
            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.process_ie_result(
                        {
                            "id": metadata.id,
                            "title": metadata.title,
                            "duration": metadata.duration,
                            "url": media_url,
                            "ext": "mp4",
                            "protocol": urlparse(media_url).scheme,
                            "http_headers": dict(options.get("http_headers") or {"User-Agent": user_agent}),
                        },
                        download=True,
                    )
                    return Path(ydl.prepare_filename(info))
            except Exception as exc:
                if isinstance(exc, TaskTimeoutError):
                    raise
                last_error = exc
                logger.warning(
                    "Provided media candidate %s/%s failed: %s",
                    index,
                    len(metadata.source_urls),
                    exc,
                )
                for partial in work_dir.glob(f"{filename_stem}.*"):
                    if partial.is_file():
                        partial.unlink(missing_ok=True)
        raise DownloadFailedError(
            "浏览器已读取视频信息，但所有媒体地址均下载失败",
            detail=str(last_error) if last_error is not None else None,
        )


def _is_douyin_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return (
        host == "douyin.com"
        or host.endswith(".douyin.com")
        or host == "iesdouyin.com"
        or host.endswith(".iesdouyin.com")
    )


def _is_xiaohongshu_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return (host == "xiaohongshu.com" or host.endswith(".xiaohongshu.com")
            or host == "xhslink.com" or host.endswith(".xhslink.com")
            or host == "xhslink.cn" or host.endswith(".xhslink.cn"))


def _normalize_xiaohongshu_url(url: str) -> str:
    for _ in range(3):
        parsed = urlparse(url)
        if not _is_xiaohongshu_url(url):
            raise DownloadFailedError("分享链接未指向小红书作品")
        if parsed.path.rstrip("/") != "/login":
            return url
        target = parse_qs(parsed.query).get("redirectPath", [""])[0]
        if not target:
            raise DownloadFailedError("小红书返回登录页，未找到原作品链接")
        url = urljoin("https://www.xiaohongshu.com/", target)
    raise DownloadFailedError("小红书分享链接出现重复登录跳转")


def _metadata_from_xiaohongshu_video(note: Any, media_id: str) -> MediaMetadata | None:
    if not isinstance(note, dict) or not _xiaohongshu_note_is_video(note):
        return None
    video = note.get("video") or {}
    streams = (video.get("media") or {}).get("stream") or {}
    urls = []
    duration = None
    for codec in ("h264", "h265", "av1", "h266"):
        variants = [v for v in streams.get(codec, []) if isinstance(v, dict)]
        variants.sort(key=lambda v: (v.get("height") or 0, v.get("avgBitrate") or 0), reverse=True)
        for variant in variants:
            for candidate in [variant.get("masterUrl"), *(variant.get("backupUrls") or [])]:
                if not isinstance(candidate, str):
                    continue
                parsed = urlparse(candidate)
                host = (parsed.hostname or "").lower()
                if (parsed.scheme in {"http", "https"} and not parsed.username and not parsed.password
                        and (host == "xhscdn.com" or host.endswith(".xhscdn.com"))):
                    if parsed.scheme == "http":
                        urls.append(parsed._replace(scheme="https").geturl())
                    urls.append(candidate)
            if duration is None and isinstance(variant.get("duration"), (int, float)):
                duration = variant["duration"] / 1000
    if not urls:
        return None
    return MediaMetadata(media_id, str(note.get("title") or note.get("desc") or media_id),
                         duration=duration, source_urls=tuple(dict.fromkeys(urls)),
                         published_at=publication_timestamp(note.get("time")))


def _xiaohongshu_mobile_options(options: dict[str, Any]) -> dict[str, Any]:
    request_options = dict(options)
    request_options["http_headers"] = {
        **options.get("http_headers", {}),
        "User-Agent": _XIAOHONGSHU_MOBILE_USER_AGENT,
    }
    return request_options


def _is_safe_media_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and parsed.port in {None, 443}
        )
    except ValueError:
        return False


def _metadata_from_xiaohongshu_note(
    note_info: Any,
    media_id: str,
) -> MediaMetadata | None:
    if not isinstance(note_info, dict) or _xiaohongshu_note_is_video(note_info):
        return None
    image_items = note_info.get("imageList")
    if not isinstance(image_items, list):
        return None

    assets: list[ImageAssetMetadata] = []
    for index, image in enumerate(image_items, start=1):
        if not isinstance(image, dict):
            continue
        image_urls = list(_xiaohongshu_original_image_urls(image))
        # Rendered H5 URLs are often downscaled and watermarked. Use them only
        # when the note does not expose an original file identifier; otherwise
        # a failed original download must be visible instead of silently
        # succeeding with a lower-quality watermarked image.
        if not image_urls:
            for key in ("urlDefault", "url", "urlPre"):
                _append_safe_url(image_urls, image.get(key))
            for image_info in image.get("infoList") or []:
                if isinstance(image_info, dict):
                    _append_safe_url(image_urls, image_info.get("url"))
        if not image_urls:
            continue

        motion_urls: list[str] = []
        stream = image.get("stream")
        if isinstance(stream, dict):
            for codec in ("h264", "h265", "av1", "h266"):
                variants = stream.get(codec)
                if not isinstance(variants, list) or not variants:
                    continue
                for variant in variants:
                    if not isinstance(variant, dict):
                        continue
                    _append_safe_url(motion_urls, variant.get("masterUrl"))
                    for backup in variant.get("backupUrls") or []:
                        _append_safe_url(motion_urls, backup)
                if motion_urls:
                    break
        assets.append(
            ImageAssetMetadata(
                index=index,
                source_urls=tuple(image_urls),
                motion_urls=tuple(motion_urls),
                width=_positive_int(image.get("width")),
                height=_positive_int(image.get("height")),
            )
        )
    if not assets:
        return None
    title = str(note_info.get("title") or note_info.get("desc") or media_id).strip()
    return MediaMetadata(
        id=media_id,
        title=title or media_id,
        kind=MediaKind.IMAGES,
        images=tuple(assets),
        image_source_policy=_XIAOHONGSHU_IMAGE_SOURCE_POLICY,
        description=str(note_info.get("desc") or "").strip(),
        published_at=publication_timestamp(note_info.get("time")),
    )


def _xiaohongshu_note_from_initial_state(
    initial_state: Any,
    media_id: str,
) -> dict[str, Any] | None:
    if not isinstance(initial_state, dict):
        return None

    mobile_note_data = initial_state.get("noteData")
    if isinstance(mobile_note_data, dict):
        mobile_data = mobile_note_data.get("data")
        mobile_note = mobile_data.get("noteData") if isinstance(mobile_data, dict) else None
        if (
            isinstance(mobile_note, dict)
            and str(mobile_note.get("noteId") or "") == media_id
        ):
            return mobile_note

    desktop_note_state = initial_state.get("note")
    if not isinstance(desktop_note_state, dict):
        return None
    note_detail_map = desktop_note_state.get("noteDetailMap")
    note_detail = note_detail_map.get(media_id) if isinstance(note_detail_map, dict) else None
    desktop_note = note_detail.get("note") if isinstance(note_detail, dict) else None
    return desktop_note if isinstance(desktop_note, dict) and desktop_note else None


def _xiaohongshu_note_is_video(note_info: dict[str, Any]) -> bool:
    note_type = str(note_info.get("type") or note_info.get("noteType") or "").lower()
    video = note_info.get("video")
    return note_type == "video" or isinstance(video, dict) and bool(video)


def _xiaohongshu_original_image_urls(image: dict[str, Any]) -> tuple[str, ...]:
    identifiers: list[str] = []
    for key in ("traceId", "fileId"):
        value = image.get(key)
        if not isinstance(value, str):
            continue
        path = value.strip().lstrip("/")
        if (
            not path
            or len(path) > 512
            or any(segment in {"", ".", ".."} for segment in path.split("/"))
        ):
            continue
        if path not in identifiers:
            identifiers.append(path)

    return tuple(
        f"https://{host}/{quote(identifier, safe='/')}"
        for identifier in identifiers
        for host in ("sns-img-qc.xhscdn.com", "sns-img-bd.xhscdn.com")
    )


def _append_safe_url(destination: list[str], value: Any) -> None:
    normalized = _normalize_media_url(value)
    if normalized is not None and normalized not in destination:
        destination.append(normalized)


def _normalize_media_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlparse(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 80, 443}
        ):
            return None
        if parsed.scheme == "http":
            parsed = parsed._replace(scheme="https", netloc=parsed.hostname)
        return parsed.geturl()
    except ValueError:
        return None


def _positive_int(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and value > 0 else None


def _content_type(response: httpx.Response) -> str:
    return response.headers.get("content-type", "").partition(";")[0].strip().lower()


async def _write_response_body_async(
    chunks: AsyncIterator[bytes],
    temporary: Path,
    first_chunk: bytes,
    deadline: float,
) -> int:
    total = len(first_chunk)
    maximum_bytes = 512 * 1024 * 1024
    with temporary.open("wb") as output:
        output.write(first_chunk)
        async for chunk in chunks:
            if time.monotonic() > deadline:
                raise TaskTimeoutError("媒体下载超时")
            total += len(chunk)
            if total > maximum_bytes:
                raise DownloadFailedError("单个媒体文件超过 512 MB 限制")
            output.write(chunk)
    if total == 0:
        raise DownloadFailedError("服务器返回了空文件")
    return total


def _image_extension(content_type: str, url: str, first_chunk: bytes) -> str | None:
    content_types = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/avif": "avif",
        "image/heic": "heic",
        "image/heif": "heif",
        "image/gif": "gif",
    }
    if extension := content_types.get(content_type.lower()):
        return extension
    if first_chunk.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if first_chunk.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if first_chunk.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if first_chunk.startswith(b"RIFF") and first_chunk[8:12] == b"WEBP":
        return "webp"
    if len(first_chunk) >= 12 and first_chunk[4:8] == b"ftyp":
        brand = first_chunk[8:12]
        if brand in {b"avif", b"avis"}:
            return "avif"
        if brand in {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}:
            return "heic"
    suffix = Path(urlparse(url).path).suffix.lower().lstrip(".")
    return suffix if suffix in {"jpg", "jpeg", "png", "webp", "avif", "heic", "heif", "gif"} else None


def _convert_heif_to_png(
    source: Path,
    temporary: Path,
    destination: Path,
) -> int:
    from PIL import Image, ImageOps
    from pillow_heif import register_heif_opener

    register_heif_opener()
    temporary.unlink(missing_ok=True)
    try:
        with Image.open(source) as original:
            transposed = ImageOps.exif_transpose(original)
            transposed.load()
            if transposed.mode not in {"1", "L", "LA", "P", "RGB", "RGBA", "I", "I;16"}:
                converted = transposed.convert(
                    "RGBA" if "A" in transposed.getbands() else "RGB"
                )
            else:
                converted = transposed
            save_options: dict[str, Any] = {
                "format": "PNG",
                "compress_level": 6,
            }
            icc_profile = original.info.get("icc_profile")
            if isinstance(icc_profile, bytes):
                save_options["icc_profile"] = icc_profile
            converted.save(temporary, **save_options)
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise DownloadFailedError("HEIF 转换后没有生成有效的 PNG 文件")
        os.replace(temporary, destination)
        return destination.stat().st_size
    finally:
        temporary.unlink(missing_ok=True)


def _looks_like_mp4(first_chunk: bytes) -> bool:
    return len(first_chunk) >= 12 and first_chunk[4:8] == b"ftyp"


def _translate_download_error(exc: Exception, url: str) -> Exception:
    if isinstance(exc, TaskTimeoutError):
        return exc
    text = str(exc).lower()
    if _is_douyin_url(url):
        if any(marker in text for marker in ("captcha", "verification required", "verify you", "验证码", "安全验证")):
            return PlatformVerificationRequiredError(detail=str(exc))
        if any(marker in text for marker in ("login required", "not logged in", "login expired", "session expired", "sign in to")):
            return CookieRefreshRequiredError(detail=str(exc))
        if any(marker in text for marker in ("http error 403", "http error 429", "status code 403", "status code 429", "too many requests")):
            return PlatformAccessRestrictedError(detail=str(exc))
        if "cookie" in text:
            return CookieCheckRequiredError(detail=str(exc))
    return DownloadFailedError(detail=str(exc))
