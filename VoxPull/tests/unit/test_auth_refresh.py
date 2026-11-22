import sqlite3
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from voxpull.domain.errors import (
    CookieMissingError, CookieRefreshRequiredError, CookieCheckRequiredError,
    DownloadFailedError, PlatformVerificationRequiredError,
    PlatformAccessRestrictedError, TaskTimeoutError,
)
from voxpull.infrastructure.chrome_auth import read_douyin_cookies
from voxpull.infrastructure.cookies import has_douyin_login_cookie, save_storage_state
from voxpull.infrastructure.downloader import _translate_download_error
from voxpull.infrastructure.video_preview import create_preview_bridge


def session():
    return {"domain": ".douyin.com", "name": "sessionid", "value": "test-only-session",
            "expires": time.time() + 3600, "path": "/", "secure": True, "httpOnly": True}


@pytest.mark.parametrize("text,expected", [
    ("Fresh cookies are needed", CookieCheckRequiredError),
    ("cookie database unavailable", CookieCheckRequiredError),
    ("captcha required", PlatformVerificationRequiredError),
    ("please verify your account", PlatformVerificationRequiredError),
    ("HTTP Error 403: Forbidden; fresh cookies needed", PlatformAccessRestrictedError),
    ("HTTP Error 429: Too Many Requests", PlatformAccessRestrictedError),
    ("login required", CookieRefreshRequiredError),
    ("session expired", CookieRefreshRequiredError),
    ("SSL CERTIFICATE_VERIFY_FAILED", DownloadFailedError),
    ("connection failed", DownloadFailedError),
])
def test_download_errors_do_not_all_mean_expired_login(text, expected):
    error = _translate_download_error(Exception(text), "https://www.douyin.com/video/123")
    assert type(error) is expected


def test_timeout_and_other_platform_are_not_reclassified_as_expired_login():
    timeout = TaskTimeoutError("cookie request timed out")
    assert _translate_download_error(timeout, "https://www.douyin.com/video/123") is timeout
    assert type(_translate_download_error(Exception("captcha"), "https://other.example/video")) is DownloadFailedError


def test_anonymous_wrong_domain_and_expired_cookies_are_not_login():
    assert has_douyin_login_cookie([session()])
    assert not has_douyin_login_cookie([{**session(), "name": "ttwid"}])
    assert not has_douyin_login_cookie([{**session(), "domain": "evildouyin.com"}])
    assert not has_douyin_login_cookie([{**session(), "expires": time.time() - 10}])



def test_chrome_reader_queries_and_decrypts_douyin_only(tmp_path):
    database = tmp_path / "Cookies"
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE meta (key TEXT, value TEXT)")
        conn.execute("INSERT INTO meta VALUES ('version','24')")
        conn.execute("CREATE TABLE cookies (host_key TEXT,name TEXT,value TEXT,encrypted_value BLOB,path TEXT,expires_utc INTEGER,is_secure INTEGER,is_httponly INTEGER,samesite INTEGER)")
        for host in (".douyin.com", ".example.com", "notdouyin.com"):
            conn.execute("INSERT INTO cookies VALUES (?,?,?,?,'/',0,1,1,1)",
                         (host, "sessionid", "", b"v10test-encrypted"))
    calls = []

    class Decryptor:
        def __init__(self, *args, **kwargs): pass
        def decrypt(self, value):
            calls.append(value)
            return "test-only-session"

    cookies = read_douyin_cookies(database, Decryptor)
    assert len(cookies) == 1 and cookies[0]["domain"] == ".douyin.com"
    assert len(calls) == 1
    assert has_douyin_login_cookie(cookies)
    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT count(*) FROM cookies").fetchone()[0] == 3


def test_failed_chrome_import_preserves_saved_state(tmp_path, monkeypatch):
    from voxpull.infrastructure import chrome_auth

    root = tmp_path / "Library/Application Support/Google/Chrome/Default"
    root.mkdir(parents=True)
    (root / "Cookies").touch()
    monkeypatch.setattr(chrome_auth.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(chrome_auth.sys, "platform", "darwin")
    monkeypatch.setattr(chrome_auth, "read_douyin_cookies", lambda _path: [])
    destination = tmp_path / "auth.json"
    save_storage_state(destination, {"cookies": [session()], "origins": []})
    original = destination.read_bytes()
    with pytest.raises(CookieMissingError):
        chrome_auth.import_chrome_douyin_state(destination)
    assert destination.read_bytes() == original


async def test_auth_bridge_requires_local_origin_and_sends_no_credentials():
    app = create_preview_bridge(18765, 1)
    browser = SimpleNamespace(import_chrome_cookies=AsyncMock(return_value="ready"),
                              auth_status=AsyncMock(return_value="ready"))
    app.state.auth_browser = browser
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        assert (await client.post("/api/auth/douyin/import-chrome")).status_code == 403
        browser.import_chrome_cookies.assert_not_awaited()
        response = await client.post("/api/auth/douyin/import-chrome", headers={"Origin": "http://127.0.0.1:18765"})
        assert response.json() == {"status": "ready"}
        browser.import_chrome_cookies.assert_awaited_once()
        assert (await client.get("/api/auth/douyin/status")).json() == {"status": "ready"}
