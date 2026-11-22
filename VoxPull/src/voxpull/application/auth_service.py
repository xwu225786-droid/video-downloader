from __future__ import annotations

from voxpull.domain.ports import BrowserPort


class AuthService:
    def __init__(self, browser: BrowserPort) -> None:
        self.browser = browser

    async def start(self, target_url: str | None = None) -> str:
        if target_url is None:
            return await self.browser.start_auth()
        return await self.browser.start_auth(target_url)

    async def complete(self) -> str:
        return await self.browser.complete_auth()

    async def status(self) -> str:
        return await self.browser.auth_status()

    async def import_chrome(self) -> str:
        return await self.browser.import_chrome_cookies()
