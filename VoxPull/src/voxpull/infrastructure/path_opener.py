from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path


class PathOpenError(RuntimeError):
    pass


class NativePathOpener:
    async def reveal(self, path: Path) -> None:
        from voxpull.infrastructure.host_bridge import bridge_configured, request_host, HostBridgeError
        if bridge_configured():
            try:
                await request_host("reveal", {"path": str(path)})
                return
            except HostBridgeError as exc:
                raise PathOpenError(str(exc)) from exc
        await asyncio.to_thread(self._reveal_sync, path)

    def _reveal_sync(self, path: Path) -> None:
        target = path.expanduser().resolve()
        if not target.exists():
            raise PathOpenError("文件或文件夹不存在")

        if sys.platform == "darwin":
            command = ["open", "-R", str(target)]
        elif sys.platform == "win32":
            command = ["explorer.exe", "/select,", str(target)]
        else:
            executable = shutil.which("xdg-open")
            if executable is None:
                raise PathOpenError("系统未安装可用的文件管理器")
            command = [executable, str(target.parent)]

        try:
            if sys.platform == "win32":
                # Explorer may report exit code 1 after handing the request to
                # an existing window. Successful process creation is sufficient.
                subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PathOpenError("无法启动系统文件管理器") from exc
        if result.returncode != 0:
            raise PathOpenError(result.stderr.strip() or "无法打开文件夹")
