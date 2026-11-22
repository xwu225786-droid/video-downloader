"""Read publicly offered Douyin works in an independent, anonymous session."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import re
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from voxpull.domain.models import BrowserEvidence, DOUYIN_GUEST_POLICY, MediaKind, MediaMetadata
from voxpull.domain.ports import DownloaderPort
from voxpull.infrastructure.browser import (
    _canonical_douyin_url, _capture_video_metadata, _media_id_from_url,
    _metadata_from_douyin_page, _select_douyin_metadata,
)
from voxpull.infrastructure.cookies import write_netscape_cookie_file


logger = logging.getLogger(__name__)
_LOGIN_TITLE = re.compile(r"^(?:Log in to Douyin|登录抖音|扫码登录|Scan to Log In)$", re.I)


async def _requires_verification(page: Page) -> bool:
    """An actual verification gate is separate from an optional login prompt."""
    path = urlparse(page.url).path.lower()
    if any(marker in path for marker in ("/captcha", "/verify", "/verifycenter")):
        return True
    for selector in ('[id*="captcha"]', '[class*="captcha-verify"]', 'iframe[src*="captcha"]'):
        if await page.locator(selector).first.is_visible():
            return True
    return False


async def _dismiss_login_prompt(page: Page) -> bool:
    """Click only a close control belonging to a visible ordinary login dialog."""
    if await _requires_verification(page):
        return False
    for frame in page.frames:
        titles = frame.get_by_text(_LOGIN_TITLE)
        for title in (await titles.all())[:4]:
            if not await title.is_visible():
                continue
            handle = await title.evaluate_handle("""(heading) => {
                const visible = (e) => {
                    const r = e.getBoundingClientRect();
                    const s = getComputedStyle(e);
                    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
                };
                let container = heading.parentElement;
                for (let depth = 0; container && depth < 10; depth++, container = container.parentElement) {
                    const box = container.getBoundingClientRect();
                    if (box.width < 250 || box.height < 120) continue;
                    if (box.width >= innerWidth * .98 && box.height >= innerHeight * .98
                        && !/login|account|dialog|modal/i.test(container.id + ' ' + container.className)
                        && container.getAttribute('role') !== 'dialog') continue;
                    if (container.querySelector('iframe[src*="captcha"], [class*="captcha-verify"]')) continue;
                    const controls = container.querySelectorAll(
                        'button,[role="button"],svg,[class*="close"],[class*="Close"],[id*="close"],[id*="Close"]'
                    );
                    for (const control of controls) {
                        if (!visible(control)) continue;
                        const r = control.getBoundingClientRect();
                        if (r.width > 64 || r.height > 64) continue;
                        const name = [control.getAttribute('aria-label'), control.getAttribute('title'),
                            control.getAttribute('class'), control.id, control.textContent].join(' ');
                        const namedClose = /close|关闭|^\\s*[×✕]\\s*$/i.test(name);
                        const corner = r.left >= box.right - 80 && r.top <= box.top + 70;
                        if (corner && (namedClose || control.tagName.toLowerCase() === 'svg')) return control;
                    }
                }
                return null;
            }""")
            try:
                control = handle.as_element()
                if control is not None:
                    await control.click(timeout=2500)
                    return True
            finally:
                await handle.dispose()
    return False


class DouyinGuestReader:
    def __init__(self, timeout_seconds: float, downloader: DownloaderPort) -> None:
        self.read_timeout_seconds = min(timeout_seconds, 30)
        self.metadata_wait_seconds = 8
        self.poll_seconds = .5
        self.downloader = downloader
        self._lock = asyncio.Lock()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._closing = False

    async def _ensure_context(self) -> None:
        if self._browser is not None and self._browser.is_connected() and self._context is not None:
            return
        await self._close_context()
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=False,
            args=["--ozone-platform=x11", "--disable-gpu"] if os.getenv("VOXPULL_BROWSER_DISPLAY_BACKEND") == "x11" else [],
        )
        # No storage_state or persistent profile: only this session's ordinary
        # anonymous cookies are used. They are never saved into the login store.
        self._context = await self._browser.new_context(viewport={"width": 1280, "height": 820})

    async def _read_media(self, page: Page, url: str, candidates: list[MediaMetadata], on_state) -> MediaMetadata | None:
        await page.goto(url, wait_until="domcontentloaded", timeout=self.read_timeout_seconds * 1000)
        host = (urlparse(page.url).hostname or "").lower()
        expected = _media_id_from_url(page.url)
        if not expected or not any(host == base or host.endswith("." + base) for base in ("douyin.com", "iesdouyin.com")):
            return None
        original = _media_id_from_url(url)
        if original and original != expected:
            return None
        deadline = asyncio.get_running_loop().time() + self.metadata_wait_seconds
        dismissed = False
        while not self._closing:
            if await _requires_verification(page):
                logger.info("event=douyin_guest_unavailable reason=verification_required")
                if on_state:
                    on_state("checking", "访客页要求验证，正在切换抖音登陆与验证窗口")
                return None
            media = _select_douyin_metadata(
                [*candidates, await _metadata_from_douyin_page(page, expected)], expected_media_id=expected,
            )
            if media is not None and _media_id_from_url(page.url) == expected:
                return media
            if not dismissed and await _dismiss_login_prompt(page):
                dismissed = True
                logger.info("event=douyin_guest_login_prompt_closed")
                if on_state:
                    on_state("guest_reading", "已关闭普通登录提示，正在重新读取公开视频资源")
                # Recheck the page and network responses after the click.
                continue
            if asyncio.get_running_loop().time() >= deadline:
                return None
            await asyncio.sleep(self.poll_seconds)
        return None

    async def acquire(self, url: str, cookie_file: Path, *,
                      on_state: Callable[[str, str], None] | None = None) -> BrowserEvidence | None:
        evidence = await self._read_evidence(url, cookie_file, on_state=on_state)
        if evidence is None:
            return None
        media = evidence.media
        downloaded = None
        try:
            if media.kind is MediaKind.VIDEO:
                media = replace(media, video_source_policy=DOUYIN_GUEST_POLICY)
                work = cookie_file.parent / "guest-video"
                work.mkdir(exist_ok=True)
                def progress(value, message):
                    if on_state:
                        on_state("guest_downloading", f"正在下载访客公开视频（{value}%）· {message}")
                downloaded = await self.downloader.download(
                    evidence.final_url, media, cookie_file, evidence.user_agent, work, progress,
                )
            logger.info("event=douyin_guest_success media_id=%s kind=%s", media.id, media.kind.value)
            if on_state:
                on_state("", "已取得访客公开资源，继续处理")
            return replace(evidence, media=media, downloaded_video=downloaded)
        except Exception as exc:
            logger.info("event=douyin_guest_unavailable reason=%s", type(exc).__name__)
            return None

    async def _read_evidence(self, url: str, cookie_file: Path, *, on_state=None) -> BrowserEvidence | None:
        if self._lock.locked() and on_state:
            on_state("guest_reading", "等待访客窗口读取公开作品")
        async with self._lock:
            if self._closing:
                return None
            if on_state:
                on_state("guest_reading", "正在以访客方式读取公开视频资源")
            page = None
            response_tasks: set[asyncio.Task] = set()
            candidates: list[MediaMetadata] = []
            try:
                async with asyncio.timeout(self.read_timeout_seconds):
                    await self._ensure_context()
                    page = await self._context.new_page()
                    def capture(response):
                        if not any(marker in response.url.lower() for marker in ("aweme/detail", "iteminfo", "item/detail", "slides")):
                            return
                        task = asyncio.create_task(_capture_video_metadata(response, candidates))
                        response_tasks.add(task)
                        task.add_done_callback(response_tasks.discard)
                    page.on("response", capture)
                    media = await self._read_media(page, url, candidates, on_state)
                    if media is None:
                        return None
                    user_agent = str(await page.evaluate("() => navigator.userAgent"))
                    write_netscape_cookie_file(await self._context.cookies(), cookie_file)
                return BrowserEvidence(_canonical_douyin_url(media), user_agent, cookie_file, media)
            except Exception as exc:
                logger.info("event=douyin_guest_unavailable reason=%s", type(exc).__name__)
                return None
            finally:
                for task in response_tasks:
                    task.cancel()
                if response_tasks:
                    await asyncio.gather(*response_tasks, return_exceptions=True)
                if page is not None:
                    with contextlib.suppress(Exception):
                        await page.close()

    async def _close_context(self) -> None:
        for target in (self._context, self._browser):
            if target is not None:
                with contextlib.suppress(Exception):
                    await target.close()
        self._context = self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def close(self) -> None:
        self._closing = True
        async with self._lock:
            await self._close_context()
