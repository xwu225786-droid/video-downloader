from __future__ import annotations

from voxpull.domain.models import SystemSnapshot
from voxpull.domain.ports import BrowserPort, SystemProbePort


class SystemService:
    def __init__(self, browser: BrowserPort, probe: SystemProbePort) -> None:
        self.browser = browser
        self.probe = probe

    async def status(self) -> SystemSnapshot:
        return await self.probe.inspect(await self.browser.auth_status())
