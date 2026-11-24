from __future__ import annotations

import importlib.metadata
import importlib.util
import platform
import shutil
from pathlib import Path

from playwright.async_api import async_playwright

from voxpull.config import Settings
from voxpull.domain.models import ComponentStatus, SystemSnapshot


class LocalSystemProbe:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def inspect(self, cookie_status: str) -> SystemSnapshot:
        playwright_ready = importlib.util.find_spec("playwright") is not None
        chromium_path = "Playwright 未安装"
        chromium_ready = False
        if playwright_ready:
            playwright = await async_playwright().start()
            try:
                chromium_path = playwright.chromium.executable_path
                chromium_ready = Path(chromium_path).is_file()
            finally:
                await playwright.stop()
        try:
            ytdlp_version = importlib.metadata.version("yt-dlp")
            ytdlp = ComponentStatus(True, ytdlp_version)
        except importlib.metadata.PackageNotFoundError:
            ytdlp = ComponentStatus(False, "yt-dlp 未安装")
        return SystemSnapshot(
            python=ComponentStatus(True, platform.python_version()),
            playwright=ComponentStatus(
                playwright_ready, "已安装" if playwright_ready else "未安装"
            ),
            chromium=ComponentStatus(chromium_ready, chromium_path),
            cookie=ComponentStatus(cookie_status == "ready", cookie_status),
            yt_dlp=ytdlp,
            ffmpeg=_binary_status(self.settings.ffmpeg_bin),
        )


def _binary_status(binary: str) -> ComponentStatus:
    resolved = shutil.which(binary)
    if resolved is None and Path(binary).is_file():
        resolved = str(Path(binary).resolve())
    return ComponentStatus(resolved is not None, resolved or f"未找到 {binary}")
