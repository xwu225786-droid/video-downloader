"""Private filesystem IPC for optional macOS actions from a local container."""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from pathlib import Path


class HostBridgeError(RuntimeError):
    pass


def bridge_directory() -> Path | None:
    value = os.getenv("VOXPULL_HOST_BRIDGE_DIR")
    return Path(value) if value else None


def bridge_configured() -> bool:
    return bridge_directory() is not None


def host_request(action: str, payload: dict | None = None, *, timeout: float = 120) -> dict:
    directory = bridge_directory()
    if directory is None:
        raise HostBridgeError("本机桥接未配置")
    health = directory / "health.json"
    try:
        alive = time.time() - health.stat().st_mtime <= 15
    except OSError:
        alive = False
    if not alive:
        raise HostBridgeError("本机桥接未运行，请使用项目的 Docker 启动入口")
    ident = uuid.uuid4().hex
    request = directory / f"{ident}.request.json"
    response = directory / f"{ident}.response.json"
    temporary = directory / f".{ident}.tmp"
    deadline = time.time() + timeout
    try:
        temporary.write_text(json.dumps({"action": action, "payload": payload or {}, "expires_at": deadline}), encoding="utf-8")
        temporary.chmod(0o600)
        os.replace(temporary, request)
        while time.time() < deadline:
            if response.is_file():
                data = json.loads(response.read_text(encoding="utf-8"))
                if not data.get("ok"):
                    raise HostBridgeError(data.get("error") or "本机操作失败")
                return data.get("result") or {}
            time.sleep(.1)
        raise HostBridgeError("等待本机操作超时，请稍后重试")
    finally:
        for path in (request, response, temporary):
            path.unlink(missing_ok=True)


async def request_host(action: str, payload: dict | None = None) -> dict:
    return await asyncio.to_thread(host_request, action, payload)
