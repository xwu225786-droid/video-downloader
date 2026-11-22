"""Opt-in macOS Chrome import; query and decrypt Douyin cookies only."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from voxpull.domain.errors import BrowserFailedError, CookieMissingError
from voxpull.infrastructure.cookies import has_douyin_login_cookie, save_storage_state


class _QuietCookieLogger:
    def debug(self, *_args, **_kwargs): pass
    def info(self, *_args, **_kwargs): pass
    def warning(self, *_args, **_kwargs): pass
    def error(self, *_args, **_kwargs): pass


def read_douyin_cookies(database: Path, decryptor_factory=None) -> list[dict[str, Any]]:
    from yt_dlp.cookies import MacChromeCookieDecryptor

    factory = decryptor_factory or MacChromeCookieDecryptor
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True, timeout=5) as conn:
        version_row = conn.execute("SELECT value FROM meta WHERE key = 'version'").fetchone()
        version = int(version_row[0]) if version_row else 0
        # Do not export the browser database or read/decrypt unrelated domains.
        rows = conn.execute("""
            SELECT host_key, name, value, encrypted_value, path, expires_utc,
                   is_secure, is_httponly, samesite
            FROM cookies WHERE host_key IN ('douyin.com', '.douyin.com', 'iesdouyin.com', '.iesdouyin.com')
                OR host_key LIKE '%.douyin.com' OR host_key LIKE '%.iesdouyin.com'
        """).fetchall()
    decryptor = None
    cookies = []
    for domain, name, value, encrypted, path, expiry, secure, http_only, same_site in rows:
        if not value and encrypted:
            if not encrypted.startswith(b"v10"):
                continue
            if decryptor is None:
                decryptor = factory("Chrome", _QuietCookieLogger(), meta_version=version)
            value = decryptor.decrypt(encrypted)
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="strict")
        if not value:
            continue
        cookies.append({
            "name": name, "value": value, "domain": domain, "path": path or "/",
            "expires": expiry / 1_000_000 - 11_644_473_600 if expiry else -1,
            "secure": bool(secure), "httpOnly": bool(http_only),
            "sameSite": {1: "Lax", 2: "Strict"}.get(same_site, "None" if secure else "Lax"),
        })
    return cookies


def import_chrome_douyin_state(destination: Path) -> None:
    from voxpull.infrastructure.host_bridge import bridge_configured, host_request, HostBridgeError
    if bridge_configured():
        try:
            host_request("import-chrome")
            if not destination.is_file():
                raise HostBridgeError("本机登录信息未出现在挂载目录，请检查Docker挂载")
            return
        except HostBridgeError as exc:
            raise BrowserFailedError(str(exc)) from exc
    if sys.platform != "darwin":
        raise BrowserFailedError("当前 Chrome 同步功能仅支持 macOS，请使用应用登录窗口")
    root = Path.home() / "Library/Application Support/Google/Chrome"
    profile = "Default"
    try:
        state = json.loads((root / "Local State").read_text())
        candidate = state.get("profile", {}).get("last_used", profile)
        if isinstance(candidate, str) and candidate not in {".", ".."} and Path(candidate).name == candidate:
            profile = candidate
    except (OSError, ValueError, TypeError):
        pass
    directory = root / profile
    database = next((path for path in (directory / "Network/Cookies", directory / "Cookies")
                     if path.is_file()), None)
    if database is None:
        raise CookieMissingError("未找到当前 Chrome 用户的 Cookie，请先在 Chrome 中登录抖音")
    try:
        cookies = read_douyin_cookies(database)
    except Exception as exc:
        raise BrowserFailedError("无法读取 Chrome 的抖音登录信息；请检查 macOS 钥匙串授权，或使用应用登录窗口") from exc
    if not has_douyin_login_cookie(cookies):
        raise CookieMissingError("Chrome 中未找到可用的抖音登录会话，或系统未允许解密；原有应用登录信息未改动")
    save_storage_state(destination, {"cookies": cookies, "origins": []})
