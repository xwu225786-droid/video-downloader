from __future__ import annotations

import asyncio
import contextlib
from dataclasses import replace
import json
import logging
import os
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Page, Playwright, Response, async_playwright

from voxpull.domain.errors import (
    BrowserFailedError,
    CookieMissingError,
    CookieRefreshRequiredError,
    DownloadFailedError,
    PlatformVerificationRequiredError,
    VoxPullError,
)
from voxpull.domain.models import (
    BrowserEvidence,
    DOUYIN_PUBLIC_SHARE_POLICY,
    DOUYIN_INTERNAL_POLICY,
    ImageAssetMetadata,
    MediaKind,
    MediaMetadata,
)
from voxpull.infrastructure.cookies import (
    has_douyin_login_cookie, save_storage_state, write_netscape_cookie_file,
)
from voxpull.infrastructure.publication import publication_timestamp
from voxpull.domain.ports import GuestReaderPort


logger = logging.getLogger(__name__)
_MOBILE_SHARE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 "
    "Mobile/15E148 Safari/604.1"
)
_DOUYIN_IMAGE_SOURCE_POLICY = "douyin-clean-live-v2"
_ROUTER_DATA_RE = re.compile(
    r"\bwindow\._ROUTER_DATA\s*=\s*(\{.*?\})\s*;?\s*</script>",
    re.IGNORECASE | re.DOTALL,
)
_REACT_FLIGHT_PREFIX = "self.__pace_f.push("


class PlaywrightBrowser:
    """One persistent browser owns login, human verification and work-page parsing."""

    def __init__(
        self, profile_dir: Path, storage_state_path: Path, timeout_seconds: float, *,
        share_fallback: Callable[[str, Path], Awaitable[BrowserEvidence | None]] | None = None,
        guest_reader: GuestReaderPort | None = None,
    ) -> None:
        self.profile_dir = profile_dir
        self.storage_state_path = storage_state_path
        self.share_fallback = share_fallback
        self.guest_reader = guest_reader
        self.share_fallback_wait_seconds = 30
        self.timeout_ms = timeout_seconds * 1000
        self.verification_wait_seconds = 900
        self.verification_poll_seconds = 1.5
        self.post_verification_grace_seconds = 15
        self._lock = asyncio.Lock()
        self._probe_lock = asyncio.Lock()
        self._acquire_lock = asyncio.Lock()
        self._auth_playwright: Playwright | None = None
        self._auth_context: BrowserContext | None = None
        self._page: Page | None = None
        self._status = self._saved_auth_status()
        self._pending_url: str | None = None
        self._expected_id: str | None = None
        self._blocked = False
        self._return_after_login = False
        self._active = False
        self._waiting = 0
        self._closing = False
        self._candidates: list[MediaMetadata] = []
        self._response_tasks: set[asyncio.Task] = set()
        self._verification_monitor: asyncio.Task | None = None
        self._operation_lock = asyncio.Lock()
        self._operation_notice: tuple[str | None, str] | None = None

    async def inspect_slider_layout(self) -> dict:
        from voxpull.infrastructure.slider_operation import inspect_layout, operation_feedback
        if self._page is None or self._page.is_closed():
            return {"status": "no_page", "frames": []}
        async with self._probe_lock:
            layout = await inspect_layout(self._page)
            layout["page_message"] = await operation_feedback(self._page)
            return layout

    async def operate_current_slider(self, still_waiting, *, allow_idle: bool = False,
                                     max_attempts: int = 1) -> dict:
        from voxpull.infrastructure.slider_operation import refresh_slider
        if not 1 <= max_attempts <= 3:
            raise ValueError("操作次数必须为1至3次")
        if self._operation_lock.locked():
            return {"status": "manual", "message": "当前已有操作在执行"}
        async with self._operation_lock:
            page, target = self._page, self._pending_url
            attempts = []
            for index in range(max_attempts):
                result = await self._operate_current_slider_once(still_waiting, allow_idle=allow_idle)
                attempts.append({"attempt": index+1, "status": result["status"],
                                 "message": result.get("message", ""),
                                 "directory": result.get("directory")})
                if result["status"] in {"passed", "performed"} or index+1 == max_attempts:
                    break
                def same_page():
                    return (still_waiting() and self._page is page and self._pending_url == target
                            and self._status == "verification_required" and not self._closing)
                if page is None or page.is_closed() or not same_page():
                    result["retry_stop_reason"] = "原页面或任务状态已改变，停止重试"
                    break
                self._operation_notice = (target, f"第{index+1}次操作未完成，正在刷新后重试（最多{max_attempts}次）")
                async with self._probe_lock:
                    refresh = await refresh_slider(page, same_page)
                attempts[-1]["refresh"] = refresh
                if not refresh["refreshed"]:
                    result["retry_stop_reason"] = refresh["message"]
                    self._operation_notice = (target, f"自动重试已停止：{refresh['message']}；请在原窗口手动处理")
                    break
            result["attempt_count"] = len(attempts)
            result["attempts"] = attempts
            if result.get("directory"):
                (Path(result["directory"]) / "retry-summary.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2))
            return result

    async def _operate_current_slider_once(self, still_waiting, *, allow_idle: bool = False) -> dict:
        from voxpull.infrastructure.host_bridge import bridge_configured, request_host
        from voxpull.infrastructure.slider_operation import operate, operation_feedback
        from voxpull.infrastructure.slider_recognition import recognize

        page = self._page
        target = self._pending_url
        def active():
            has_owner = self._active or (allow_idle and not self._acquire_lock.locked())
            return (still_waiting() and has_owner and not self._closing
                    and self._page is page and self._status == "verification_required")
        if page is None or page.is_closed() or not active():
            return {"status": "manual", "message": "原任务当前没有可操作的页面"}
        async def predict(image):
            async with asyncio.timeout(25):
                if bridge_configured():
                    return await request_host("recognize-slider", {"image": image})
                return await asyncio.to_thread(recognize, {"image": image})
        async with self._probe_lock:
            self._operation_notice = None
            result = await operate(page, predict, active,
                                   self.storage_state_path.parent.parent / "logs/slider-operations")
        if result["status"] == "performed":
            for _ in range(80):
                await asyncio.sleep(.25)
                if self._page is not page or self._pending_url != target or page.is_closed():
                    break
                status, media = await self._inspect_page()
                result["page_status"] = status
                if status == "ready" and media is not None:
                    result.update(status="passed", message="滑块操作后原作品已取得播放信息")
                    break
                feedback = await operation_feedback(page)
                if feedback:
                    result["page_message"] = feedback
                if any(word in feedback for word in ("操作过快", "验证失败", "网络异常")):
                    result.update(status="rejected", message=feedback)
                    break
            if self._page is page and not page.is_closed():
                try:
                    await page.screenshot(path=str(Path(result["directory"]) / "result.png"),
                                          scale="css", timeout=3000)
                except Exception:
                    result["result_screenshot_error"] = "无法保存最终页面截图"
            (Path(result["directory"]) / "report.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2))
        if result["status"] in {"manual", "rejected", "performed"}:
            label = {"manual": "自动操作未完成", "rejected": "平台拒绝本次操作",
                     "performed": "已执行拖动，但尚未确认通过"}[result["status"]]
            self._operation_notice = (target, f"{label}：{result.get('message', '')}；"
                                     "请在原窗口手动处理，任务继续等待")
        return result


    def _saved_auth_status(self) -> str:
        try:
            state = json.loads(self.storage_state_path.read_text(encoding="utf-8"))
            return "saved" if has_douyin_login_cookie(state.get("cookies", [])) else "missing"
        except (OSError, ValueError, TypeError):
            return "missing"

    def auth_details(self) -> dict:
        return {"target_url": self._pending_url, "waiting_jobs": self._waiting + int(self._active),
                "session_shared": True, "active_job": self._active}

    async def _open_auth_context(self, *, headless: bool = False) -> None:
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        profile_cookie_time = max((p.stat().st_mtime_ns for p in (
            self.profile_dir / "Default/Cookies", self.profile_dir / "Default/Cookies-wal",
            self.profile_dir / "Default/Network/Cookies", self.profile_dir / "Default/Network/Cookies-wal",
        ) if p.is_file()), default=0)
        self._auth_playwright = await async_playwright().start()
        self._auth_context = await self._auth_playwright.chromium.launch_persistent_context(
            str(self.profile_dir), headless=headless,
            args=["--ozone-platform=x11", "--disable-gpu"] if os.getenv("VOXPULL_BROWSER_DISPLAY_BACKEND") == "x11" else [],
            viewport={"width": 1280, "height": 820},
        )
        if self.storage_state_path.is_file():
            state = json.loads(self.storage_state_path.read_text(encoding="utf-8"))
            profile_has_login = has_douyin_login_cookie(await self._auth_context.cookies())
            if state.get("cookies") and (not profile_has_login or self.storage_state_path.stat().st_mtime_ns > profile_cookie_time):
                await self._auth_context.add_cookies(state["cookies"])

    async def _ensure_context(self) -> None:
        async with self._lock:
            if self._auth_context is not None and self._auth_context.pages:
                return
            await self._close_auth_context()
            await self._open_auth_context(headless=False)
            self._page = None

    async def _window(self, state: str) -> None:
        if self._page is None or self._page.is_closed():
            return
        try:
            session = await self._auth_context.new_cdp_session(self._page)
            try:
                window = await session.send("Browser.getWindowForTarget")
                await session.send("Browser.setWindowBounds", {"windowId": window["windowId"],
                                                               "bounds": {"windowState": state}})
            finally:
                await session.detach()
        except Exception:
            logger.debug("Window state update unavailable", exc_info=False)
        if state == "normal":
            with contextlib.suppress(Exception):
                await self._page.bring_to_front()

    async def _ensure_page(self) -> None:
        if self._page is None or self._page.is_closed():
            self._page = self._auth_context.pages[0] if self._auth_context.pages else await self._auth_context.new_page()
            def capture(response):
                if not any(key in response.url.lower() for key in ("aweme/detail", "iteminfo", "item/detail", "slides")):
                    return
                task = asyncio.create_task(_capture_video_metadata(response, self._candidates))
                self._response_tasks.add(task)
                task.add_done_callback(self._response_tasks.discard)
            self._page.on("response", capture)

    async def _navigate(self, url: str) -> None:
        await self._ensure_page()
        self._candidates.clear()
        self._pending_url = url
        self._operation_notice = None
        self._expected_id = _media_id_from_url(url)
        self._status = "checking"
        await self._page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        await self._page.wait_for_timeout(4000)

    async def _save_auth_context(self) -> str:
        save_storage_state(self.storage_state_path, await self._auth_context.storage_state())
        self._status = "ready"
        self._blocked = False
        self._return_after_login = False
        return "ready"

    async def _inspect_page(self) -> tuple[str, MediaMetadata | None]:
        async with self._probe_lock:
            if self._page is None or self._page.is_closed():
                if self._blocked:
                    self._status = "window_closed"
                return self._status, None
            if await _page_requires_auth_action(self._page):
                path = urlparse(self._page.url).path.lower()
                self._status = "opening" if any(p in path for p in ("/login", "/passport")) else "verification_required"
                self._blocked = True
                self._return_after_login = self._status == "opening"
                return self._status, None
            if self._expected_id is not None:
                media = await _metadata_from_douyin_page(self._page, self._expected_id)
                media = _select_douyin_metadata([*self._candidates, media], expected_media_id=self._expected_id)
                if _media_id_from_url(self._page.url) != self._expected_id:
                    media = None
                if media is not None:
                    await self._save_auth_context()
                    return "ready", media
                if not has_douyin_login_cookie(await self._auth_context.cookies()):
                    self._status = "opening"
                    self._blocked = True
                    self._return_after_login = True
                else:
                    self._status = "checking"
                return self._status, None
            if has_douyin_login_cookie(await self._auth_context.cookies()):
                await self._save_auth_context()
                return "ready", None
            self._status = "opening"
            self._blocked = True
            return self._status, None

    async def start_auth(self, target_url: str | None = None) -> str:
        try:
            await self._ensure_context()
            await self._ensure_page()
            # Show the window before network access, so a slow page cannot leave
            # the user looking at an empty verification desktop.
            await self._window("normal")
            if self._active and not self._blocked:
                return self._status
            has_work_page = self._page.url not in {"about:blank", ""}
            if not self._active and not self._blocked and (target_url or not has_work_page):
                # Explicit task requests use the actual work page, not the homepage.
                target = await self._resolve_work_url(target_url) if target_url else self._pending_url or "https://www.douyin.com/"
                await self._navigate(target)
            elif self._blocked and not has_work_page:
                await self._navigate(self._pending_url or target_url or "https://www.douyin.com/")
            await self._window("normal")
            status, _ = await self._inspect_page()
            if self._blocked:
                self._start_verification_monitor()
            return status
        except VoxPullError:
            raise
        except Exception as exc:
            self._status = "error"
            raise BrowserFailedError("无法打开抖音登陆与验证窗口，请关闭其他应用登录窗口后重试") from exc

    async def complete_auth(self) -> str:
        if self._auth_context is None:
            return self._saved_auth_status()
        if self._page is None or self._page.is_closed():
            self._status = "window_closed" if self._blocked else self._saved_auth_status()
            return self._status
        status, _ = await self._inspect_page()
        if status == "checking" and self._return_after_login and self._pending_url:
            self._return_after_login = False
            await self._navigate(self._pending_url)
            status, _ = await self._inspect_page()
        if status in {"verification_required", "opening", "checking", "window_closed"}:
            return status
        if not has_douyin_login_cookie(await self._auth_context.cookies()):
            raise CookieMissingError("尚未检测到登录会话，请先在当前作品页登录；窗口已保留")
        return status

    async def auth_status(self) -> str:
        if self._auth_context is None:
            return self._status if self._blocked else self._saved_auth_status()
        # GET never navigates or closes the shared context; it only observes the current page.
        if self._page is not None:
            try:
                status, _ = await self._inspect_page()
                return status
            except Exception:
                if self._page.is_closed():
                    self._status = "window_closed"
                return self._status
        return self._status

    async def import_chrome_cookies(self) -> str:
        from voxpull.infrastructure.chrome_auth import import_chrome_douyin_state
        async with self._lock:
            if self._active or self._blocked:
                raise BrowserFailedError("请先在当前作品窗口完成验证；任务等待期间不替换浏览器会话")
            await asyncio.to_thread(import_chrome_douyin_state, self.storage_state_path)
            if self._auth_context is not None:
                saved = json.loads(self.storage_state_path.read_text(encoding="utf-8"))
                await self._auth_context.add_cookies(saved.get("cookies", []))
                save_storage_state(self.storage_state_path, await self._auth_context.storage_state())
            self._status = "saved"
            return "saved"

    def _start_verification_monitor(self) -> None:
        if self._verification_monitor is not None and not self._verification_monitor.done():
            return
        async def observe():
            while self._blocked and not self._closing:
                try:
                    await self._inspect_page()
                    if self._page is None or self._page.is_closed():
                        break
                except Exception:
                    if self._page is None or self._page.is_closed():
                        break
                    logger.debug("Verification observation will retry", exc_info=False)
                await asyncio.sleep(0.5)
        self._verification_monitor = asyncio.create_task(observe(), name="douyin-verification-observer")

    async def _wait_for_access(
        self, on_state=None, *, share_url: str | None = None, cookie_file: Path | None = None,
    ) -> MediaMetadata | BrowserEvidence | None:
        last = None
        checking_since = None
        share_deadline = None
        tried_share = False
        share_unavailable = False
        deadline = asyncio.get_running_loop().time() + self.verification_wait_seconds
        await self._window("normal")
        self._start_verification_monitor()
        while not self._closing:
            try:
                status, media = await self._inspect_page()
            except Exception:
                if self._page is None or self._page.is_closed():
                    status, media = "window_closed", None
                    self._status = status
                else:
                    raise
            if status == "ready":
                if on_state:
                    on_state("checking", "验证已通过，正在继续获取当前作品")
                return media
            now = asyncio.get_running_loop().time()
            if now >= deadline:
                # Keep the page so a retry can use the same verification session.
                reason = "分享页未提供可下载视频，且人工验证等待已超时" if share_unavailable else "等待人工登录或验证超时"
                raise PlatformVerificationRequiredError(f"{reason}；当前作品窗口已保留，完成后可单独重试")
            if status == "verification_required" and self.share_fallback and share_url and cookie_file:
                if share_deadline is None:
                    share_deadline = now + self.share_fallback_wait_seconds
                if not tried_share and now >= share_deadline:
                    tried_share = True
                    try:
                        async with asyncio.timeout(deadline - now):
                            evidence = await self._try_public_share(share_url, cookie_file, on_state)
                    except TimeoutError:
                        evidence = None
                    if evidence is not None:
                        return evidence
                    share_unavailable = True
                    continue
            if status == "checking" and self._return_after_login and self._pending_url:
                self._return_after_login = False
                await self._navigate(self._pending_url)
                continue
            if status == "checking":
                checking_since = checking_since or asyncio.get_running_loop().time()
                if asyncio.get_running_loop().time() - checking_since > self.post_verification_grace_seconds:
                    self._blocked = False
                    self._status = self._saved_auth_status()
                    raise DownloadFailedError("验证界面已结束，但当前作品仍未取得播放信息；可单独重试，其他作品可继续")
            else:
                checking_since = None
            remaining = max(0, deadline - asyncio.get_running_loop().time())
            operation_notice = (self._operation_notice[1] if self._operation_notice
                                and self._operation_notice[0] == self._pending_url else None)
            notice = (status, share_unavailable, int(remaining // 30), operation_notice)
            if notice != last and on_state:
                messages = {"opening": "等待在当前作品窗口登录，完成后自动继续",
                            "verification_required": "等待手动完成当前作品的验证，完成后自动继续",
                            "window_closed": "验证窗口已关闭，请点击继续验证重新打开；任务仍在等待",
                            "checking": "正在确认当前作品已通过验证"}
                message = messages.get(status, "等待当前浏览器会话完成验证")
                if operation_notice and status == "verification_required":
                    message = operation_notice
                if share_unavailable:
                    message = f"分享页未提供可下载视频，{message}"
                elif (status == "verification_required" and share_deadline is not None
                      and not tried_share and not operation_notice):
                    seconds = max(0, int(share_deadline - asyncio.get_running_loop().time()))
                    message = f"等待滑块验证，约{seconds}秒后尝试公开分享页"
                minutes = max(1, int((remaining + 59) // 60))
                on_state(status, f"{message}（剩余最多{minutes}分钟）")
                last = notice
            await asyncio.sleep(self.verification_poll_seconds)
        raise BrowserFailedError("应用正在关闭，当前验证等待已结束")

    async def _resolve_work_url(self, url: str) -> str:
        resolved = url
        if _media_id_from_url(resolved) is None:
            response = await self._auth_context.request.get(url, timeout=self.timeout_ms)
            resolved = response.url
            await response.dispose()
        ident = _media_id_from_url(resolved)
        if ident is None:
            raise DownloadFailedError("未能从分享链接识别作品 ID")
        route = "note" if any(x in urlparse(resolved).path for x in ("/note/", "/slides/", "/gallery/")) else "video"
        return f"https://www.douyin.com/{route}/{ident}"

    async def acquire(self, url: str, cookie_file: Path, *, on_state=None) -> BrowserEvidence:
        if self._closing:
            raise BrowserFailedError("应用正在关闭")
        # Public work pages do not need to wait behind another job's login gate.
        # The reader has its own lock and never imports or replaces saved auth.
        if self.guest_reader is not None:
            try:
                evidence = await self.guest_reader.acquire(url, cookie_file, on_state=on_state)
            except Exception as exc:
                logger.info("event=douyin_guest_unavailable reason=%s", type(exc).__name__)
                evidence = None
            if evidence is not None:
                return evidence
            if on_state:
                on_state("checking", "访客页未取得可用资源，正在切换抖音登陆与验证窗口")
        if self._acquire_lock.locked() and on_state:
            on_state("waiting_browser", "等待前一个抖音任务使用完登陆与验证窗口，暂不访问新链接")
        self._waiting += 1
        entered = False
        try:
            async with self._acquire_lock:
                self._waiting -= 1
                entered = True
                self._active = True
                try:
                    if self._blocked:
                        pending = await self._wait_for_access(on_state, share_url=url, cookie_file=cookie_file)
                        if isinstance(pending, BrowserEvidence):
                            return pending
                    await self._ensure_context()
                    if on_state:
                        on_state("checking", "正在使用抖音窗口读取作品")
                    navigation = await self._resolve_work_url(url)
                    route = "note" if "/note/" in navigation else "video"
                    await self._navigate(navigation)
                    status, media = await self._inspect_page()
                    # Loading and an iframe challenge may arrive after DOMContentLoaded.
                    # Keep the task alive while deciding whether access is blocked.
                    checking_deadline = (asyncio.get_running_loop().time()
                                         + self.post_verification_grace_seconds)
                    while media is None and not self._blocked and status == "checking":
                        if asyncio.get_running_loop().time() >= checking_deadline:
                            break
                        await asyncio.sleep(self.verification_poll_seconds)
                        status, media = await self._inspect_page()
                    if self._blocked:
                        media = await self._wait_for_access(on_state, share_url=navigation, cookie_file=cookie_file)
                        if isinstance(media, BrowserEvidence):
                            return media
                    if media is None and route == "note":
                        candidate = await _acquire_mobile_share_metadata(self._auth_context, url, timeout_ms=self.timeout_ms)
                        if candidate is not None and candidate.kind is MediaKind.IMAGES:
                            media = candidate
                    if media is None:
                        self._status = self._saved_auth_status()
                        raise DownloadFailedError("未取得抖音站内播放源，作品可能不可用或访问受限")
                    if media.kind is MediaKind.VIDEO:
                        media = replace(media, video_source_policy=DOUYIN_INTERNAL_POLICY)
                    cookies = await self._auth_context.cookies()
                    if not _has_douyin_cookie(cookies):
                        self._status = "refresh_required"
                        raise CookieRefreshRequiredError("未能取得抖音浏览会话，请在当前窗口登录")
                    await self._save_auth_context()
                    write_netscape_cookie_file(cookies, cookie_file)
                    if on_state:
                        on_state("", "已取得作品信息，继续下载")
                    # A minimized window is an empty desktop in the Docker
                    # verification viewer; keep its browser visible there.
                    if not os.getenv("VOXPULL_BROWSER_CONSOLE_URL"):
                        await self._window("minimized")
                    return BrowserEvidence(_canonical_douyin_url(media), str(await self._page.evaluate("() => navigator.userAgent")), cookie_file, media)
                except VoxPullError:
                    raise
                except Exception as exc:
                    logger.exception("Shared Douyin browser failed")
                    self._status = "error"
                    raise BrowserFailedError(detail=str(exc)) from exc
                finally:
                    self._active = False
        finally:
            if not entered:
                self._waiting -= 1

    async def _try_public_share(self, url: str, cookie_file: Path, on_state) -> BrowserEvidence | None:
        if self.share_fallback is None:
            return None
        if on_state:
            on_state("verification_required", "滑块验证待处理，正在尝试公开分享页的水印版")
        logger.info("event=douyin_public_share_attempt")
        evidence = await self.share_fallback(url, cookie_file)
        logger.info("event=douyin_public_share_result available=%s", evidence is not None)
        return evidence

    async def close(self) -> None:
        self._closing = True
        if self.guest_reader is not None:
            await self.guest_reader.close()
        if self._verification_monitor is not None:
            self._verification_monitor.cancel()
            await asyncio.gather(self._verification_monitor, return_exceptions=True)
        async with self._lock:
            await self._close_auth_context()

    async def _close_auth_context(self) -> None:
        if self._auth_context is not None:
            with contextlib.suppress(Exception):
                await self._auth_context.close()
            self._auth_context = None
        self._page = None
        if self._auth_playwright is not None:
            with contextlib.suppress(Exception):
                await self._auth_playwright.stop()
            self._auth_playwright = None
        for task in tuple(self._response_tasks):
            task.cancel()
        if self._response_tasks:
            await asyncio.gather(*tuple(self._response_tasks), return_exceptions=True)


def _has_douyin_cookie(cookies: list[dict[str, object]]) -> bool:
    return any(
        str(cookie.get("domain", "")).removeprefix(".").endswith("douyin.com") for cookie in cookies
    )


async def _acquire_mobile_share_metadata(
    context: BrowserContext, url: str, timeout_ms: float
) -> MediaMetadata | None:
    response = None
    try:
        response = await context.request.get(
            url,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": _MOBILE_SHARE_USER_AGENT,
            },
            timeout=timeout_ms,
        )
        if not response.ok:
            logger.debug("Douyin mobile share page returned HTTP %s", response.status)
            return None
        expected_media_id = _media_id_from_url(response.url)
        if expected_media_id is None:
            logger.debug("Douyin mobile share page did not resolve to a supported work URL")
            return None
        return _metadata_from_mobile_share_html(await response.text(), expected_media_id)
    except Exception:
        # Keep the existing browser/API path as a fallback for pages whose
        # mobile representation is unavailable.
        logger.debug("Unable to read Douyin mobile share metadata", exc_info=True)
        return None
    finally:
        if response is not None:
            with contextlib.suppress(Exception):
                await response.dispose()


def _metadata_from_mobile_share_html(
    html: str, expected_media_id: str, *, public_watermarked: bool = False,
) -> MediaMetadata | None:
    match = _ROUTER_DATA_RE.search(html)
    if match is None:
        return None
    try:
        payload = json.loads(match.group(1))
    except (TypeError, ValueError):
        return None

    for detail in _find_aweme_details(payload):
        metadata = _metadata_from_aweme_detail(detail, public_watermarked=public_watermarked)
        if metadata is not None and metadata.id == expected_media_id:
            return metadata
    return None


async def _metadata_from_douyin_page(
    page: Page, expected_media_id: str
) -> MediaMetadata | None:
    script_texts = await page.locator("script").all_text_contents()
    return _metadata_from_react_flight_scripts(script_texts, expected_media_id)


def _metadata_from_react_flight_scripts(
    script_texts: list[str], expected_media_id: str
) -> MediaMetadata | None:
    for script_text in script_texts:
        text = script_text.strip()
        if (
            not text.startswith(_REACT_FLIGHT_PREFIX)
            or not text.endswith(")")
            or expected_media_id not in text
        ):
            continue
        try:
            packet = json.loads(text[len(_REACT_FLIGHT_PREFIX) : -1])
            serialized = packet[1]
            if not isinstance(serialized, str):
                continue
            _, separator, payload_text = serialized.partition(":")
            if not separator:
                continue
            payload = json.loads(payload_text.strip())
        except (IndexError, TypeError, ValueError):
            continue
        for detail in _find_aweme_details(payload):
            metadata = _metadata_from_aweme_detail(detail)
            if metadata is not None and metadata.id == expected_media_id:
                return metadata
    return None


async def _capture_video_metadata(
    response: Response, destination: list[MediaMetadata]
) -> None:
    if response.status != 200:
        return
    try:
        payload = await response.json()
        metadata = next(
            (
                candidate
                for detail in _find_aweme_details(payload)
                if (candidate := _metadata_from_aweme_detail(detail)) is not None
            ),
            None,
        )
    except Exception:
        logger.debug("Unable to read browser-provided Douyin metadata", exc_info=True)
        return
    if metadata is not None:
        destination.append(metadata)


def _select_douyin_metadata(
    candidates: list[MediaMetadata | None],
    *,
    expected_media_id: str | None,
) -> MediaMetadata | None:
    matching = [
        candidate
        for candidate in candidates
        if candidate is not None
        and (expected_media_id is None or candidate.id == expected_media_id)
    ]
    if not matching:
        return None
    return max(matching, key=_douyin_metadata_quality)


def _douyin_metadata_quality(metadata: MediaMetadata) -> tuple[int, int, int, int, int]:
    if metadata.kind is MediaKind.IMAGES:
        live_count = sum(asset.is_live for asset in metadata.images)
        motion_candidate_count = sum(len(asset.motion_urls) for asset in metadata.images)
        return (
            2,
            live_count,
            motion_candidate_count,
            len(metadata.images),
            sum(len(asset.source_urls) for asset in metadata.images),
        )
    pixels = (metadata.video_width or 0) * (metadata.video_height or 0)
    return (1, pixels, metadata.video_bitrate or 0, int(bool(metadata.source_urls)), len(metadata.source_urls))


def _ranked_douyin_playback(video: dict) -> tuple[list[str], tuple[int, int, int]]:
    """Keep quality ahead of CDN preference; defaults may only be 540p."""
    candidates = {}
    def add(address, bitrate=0):
        urls: list[str] = []
        _extend_address_urls(urls, address)
        values = address if isinstance(address, dict) else {}
        width = _positive_int(values.get("width")) or 0
        height = _positive_int(values.get("height")) or 0
        size = _positive_int(values.get("data_size") or values.get("dataSize")) or 0
        rate = _positive_int(bitrate) or _positive_int(values.get("bit_rate")) or 0
        duration = video.get("duration")
        if not rate and size and isinstance(duration, (int, float)) and duration > 0:
            rate = int(size * 8000 / duration)
        # Do not use the video's top-level size for an address: a 1080p
        # original may expose a 576x1024 default playback address.
        quality = (width * height, min(width, height), rate, size)
        for value in urls:
            url = _internal_playback_url(value)
            if url is None:
                continue
            cdn = int(urlparse(url).hostname not in {"douyin.com", "www.douyin.com"})
            rank = (*quality, cdn)
            if url not in candidates or rank > candidates[url][0]:
                candidates[url] = (rank, (width, height, rate))
    for key in ("play_addr_h264", "play_addr", "play_addr_bytevc1", "play_addr_265", "playAddrH264", "playAddr"):
        add(video.get(key))
    variants = video.get("bit_rate") or video.get("bitRateList") or []
    if isinstance(variants, list):
        for variant in variants:
            if isinstance(variant, dict):
                for key in ("play_addr", "playAddr", "play_addr_h264", "play_addr_bytevc1"):
                    add(variant.get(key), variant.get("bit_rate") or variant.get("bitRate"))
    urls = sorted(candidates, key=lambda url: candidates[url][0], reverse=True)
    return urls, candidates[urls[0]][1] if urls else (0, 0, 0)


def _metadata_from_aweme_detail(detail: Any, *, public_watermarked: bool = False) -> MediaMetadata | None:
    if not isinstance(detail, dict):
        return None
    media_id = str(detail.get("aweme_id") or detail.get("awemeId") or detail.get("id") or "")
    if not media_id.isdigit():
        return None
    title = str(
        detail.get("desc")
        or detail.get("item_title")
        or detail.get("itemTitle")
        or media_id
    ).strip() or media_id

    image_assets = _image_assets_from_aweme_detail(detail)
    if image_assets:
        if public_watermarked:
            return None
        return MediaMetadata(
            id=media_id,
            title=title,
            kind=MediaKind.IMAGES,
            images=tuple(image_assets),
            image_source_policy=_DOUYIN_IMAGE_SOURCE_POLICY,
            published_at=publication_timestamp(detail.get("create_time") or detail.get("createTime")),
        )

    video = detail.get("video")
    if not isinstance(video, dict):
        return None

    urls: list[str] = []
    width, height, bitrate = 0, 0, 0
    if public_watermarked:
        for key in ("play_addr_h264", "play_addr", "play_addr_bytevc1", "playAddrH264", "playAddr"):
            _extend_address_urls(urls, video.get(key))
        control = detail.get("video_control")
        if isinstance(control, dict) and control.get("allow_download") in (False, 0):
            return None
        urls = [url for url in urls if _is_watermarked_playback(url)]
        for key in ("download_addr", "downloadAddr"):
            _extend_address_urls(urls, video.get(key))
    else:
        urls, (width, height, bitrate) = _ranked_douyin_playback(video)
    if not urls:
        return None

    # Prefer direct CDN URLs. The www.douyin.com fallback works, but is more
    # sensitive to short-lived request signatures and anti-bot checks.
    if public_watermarked:
        urls.sort(key=lambda value: urlparse(value).hostname in {"douyin.com", "www.douyin.com"})
    duration_ms = video.get("duration") or detail.get("duration")
    duration = (
        float(duration_ms) / 1000
        if isinstance(duration_ms, (int, float)) and duration_ms >= 0
        else None
    )
    return MediaMetadata(
        id=media_id,
        title=title,
        kind=MediaKind.VIDEO,
        duration=duration,
        source_urls=tuple(urls),
        published_at=publication_timestamp(detail.get("create_time") or detail.get("createTime")),
        video_source_policy=DOUYIN_PUBLIC_SHARE_POLICY if public_watermarked else None,
        video_width=width or None,
        video_height=height or None,
        video_bitrate=bitrate or None,
    )


def _is_watermarked_playback(url: str) -> bool:
    parsed = urlparse(url)
    return "playwm" in parsed.path.lower() or bool(re.search(r"(?:^|&)(?:watermark|watermark_type)=1(?:&|$)", parsed.query))


def _internal_playback_url(url: str) -> str | None:
    parsed = urlparse(url)
    # Only the known platform playback endpoint can be normalized. Signed CDN
    # paths are never rewritten. Explicit watermark resources are not fallback.
    host = (parsed.hostname or "").lower()
    platform = host == "douyin.com" or host.endswith(".douyin.com") or host == "iesdouyin.com" or host.endswith(".iesdouyin.com")
    if "/aweme/v1/playwm/" in parsed.path and platform:
        parsed = parsed._replace(path=parsed.path.replace("/aweme/v1/playwm/", "/aweme/v1/play/"))
        url = parsed.geturl()
    if _is_watermarked_playback(url):
        return None
    return url


def _image_assets_from_aweme_detail(detail: dict[str, Any]) -> list[ImageAssetMetadata]:
    image_items: list[Any] = []
    if isinstance(detail.get("images"), list):
        image_items.extend(detail["images"])
    image_post_info = detail.get("image_post_info")
    if isinstance(image_post_info, dict) and isinstance(image_post_info.get("images"), list):
        image_items.extend(image_post_info["images"])

    assets: list[ImageAssetMetadata] = []
    seen_still_urls: set[str] = set()
    for image in image_items:
        if not isinstance(image, dict):
            continue
        still_urls: list[str] = []
        for key in (
            "download_url",
            "downloadUrlList",
            "download_url_list",
            "download_image",
            "display_image",
            "origin_image",
            "image",
        ):
            _extend_address_urls(still_urls, image.get(key))
        _extend_address_urls(still_urls, image)

        # Douyin commonly exposes signed `new-water` download URLs before the
        # otherwise identical `new` render. When a clean render exists, do not
        # retain explicit watermarked variants as download fallbacks: a
        # transient CDN failure must not silently replace the archived image
        # with a watermarked copy.
        still_urls.sort(key=_douyin_image_url_priority)
        clean_urls = [url for url in still_urls if _douyin_image_url_priority(url) < 2]
        if clean_urls:
            still_urls = clean_urls
        still_urls = [url for url in still_urls if url not in seen_still_urls]
        owner_watermark_urls: list[str] = []
        _extend_address_urls(owner_watermark_urls, image.get("owner_watermark_image"))
        if not clean_urls:
            still_urls.extend(
                url
                for url in owner_watermark_urls
                if url not in seen_still_urls and url not in still_urls
            )
        if not still_urls:
            continue
        seen_still_urls.update(still_urls)

        motion_urls: list[str] = []
        for key in (
            "video",
            "video_info",
            "clip_video",
            "live_photo",
            "livePhoto",
            "motion",
        ):
            _extend_video_urls(motion_urls, image.get(key))
        assets.append(
            ImageAssetMetadata(
                index=len(assets) + 1,
                source_urls=tuple(still_urls),
                motion_urls=tuple(motion_urls),
                width=_positive_int(image.get("width")),
                height=_positive_int(image.get("height")),
            )
        )
    return assets


def _douyin_image_url_priority(url: str) -> int:
    lowered = url.lower()
    if any(
        marker in lowered
        for marker in (
            "tplv-dy-lqen-new-water",
            "tplv-dy-water",
            "owner_watermark",
            "owner-watermark",
            "water_mark",
            "watermark",
        )
    ):
        return 2
    if any(
        marker in lowered
        for marker in (
            "tplv-dy-lqen-new:",
            "tplv-dy-lqen-new%3a",
            "tplv-dy-aweme-images:",
            "tplv-dy-aweme-images%3a",
        )
    ):
        return 0
    return 1


def _extend_address_urls(destination: list[str], value: Any) -> None:
    if _is_safe_media_url(value):
        if value not in destination:
            destination.append(value)
        return
    if isinstance(value, list):
        for item in value:
            _extend_address_urls(destination, item)
        return
    if not isinstance(value, dict):
        return
    for key in (
        "download_url_list",
        "downloadUrlList",
        "url_list",
        "urlList",
        "urls",
        "url",
        "src",
    ):
        _extend_address_urls(destination, value.get(key))


def _extend_video_urls(destination: list[str], value: Any) -> None:
    if not isinstance(value, dict):
        return
    for key in (
        "play_addr_h264",
        "play_addr",
        "download_addr",
        "playAddr",
        "downloadAddr",
        "master_url",
        "masterUrl",
    ):
        _extend_address_urls(destination, value.get(key))
    for key in ("video", "video_info", "play_info", "resource"):
        nested = value.get(key)
        if isinstance(nested, dict):
            _extend_video_urls(destination, nested)


def _find_aweme_details(value: Any):
    if isinstance(value, dict):
        if value.get("aweme_id") or value.get("awemeId") or (
            str(value.get("id") or "").isdigit()
            and (value.get("video") or value.get("images") or value.get("image_post_info"))
        ):
            yield value
        for nested in value.values():
            yield from _find_aweme_details(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _find_aweme_details(nested)


def _positive_int(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and value > 0 else None


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


def _media_id_from_url(url: str) -> str | None:
    parts = urlparse(url).path.rstrip("/").split("/")
    if (
        len(parts) >= 2
        and parts[-2] in {"video", "note", "slides", "gallery"}
        and parts[-1].isdigit()
    ):
        return parts[-1]
    return None


def _video_id_from_url(url: str) -> str | None:
    parts = urlparse(url).path.rstrip("/").split("/")
    return parts[-1] if len(parts) >= 2 and parts[-2] == "video" and parts[-1].isdigit() else None


def _canonical_douyin_url(metadata: MediaMetadata) -> str:
    route = "video" if metadata.kind is MediaKind.VIDEO else "note"
    return f"https://www.douyin.com/{route}/{metadata.id}"


def _auth_page_requires_interaction(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(marker in path for marker in ("/login", "/captcha", "/verify", "/passport"))


async def _page_requires_auth_action(page: Page) -> bool:
    if _auth_page_requires_interaction(page.url):
        return True
    for frame in getattr(page, "frames", [page]):
        try:
            if frame is not page and getattr(page, "main_frame", frame) is not frame:
                if not await (await frame.frame_element()).is_visible():
                    continue
            for selector in ('[id*="captcha"]', '[class*="captcha-verify"]',
                             '.vc-captcha-verify', 'iframe[src*="captcha"]'):
                if await frame.locator(selector).first.is_visible():
                    return True
        except Exception:
            # A frame can detach while the page switches to the actual work.
            continue
    return False
