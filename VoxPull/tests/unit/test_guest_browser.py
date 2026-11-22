import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from voxpull.domain.errors import DownloadFailedError
from voxpull.domain.models import DOUYIN_GUEST_POLICY, MediaMetadata
from voxpull.infrastructure.douyin_guest import DouyinGuestReader


async def reader_fixture(tmp_path, monkeypatch, *, media=True, challenge=False):
    import voxpull.infrastructure.douyin_guest as module
    page = SimpleNamespace(
        url="https://www.douyin.com/video/123", challenge=challenge,
        media=MediaMetadata("123", "公开作品", source_urls=("https://cdn.test/video.mp4",)) if media else None,
        goto=AsyncMock(), close=AsyncMock(), evaluate=AsyncMock(return_value="guest-agent"), on=lambda *_: None,
    )
    context = SimpleNamespace(new_page=AsyncMock(return_value=page), close=AsyncMock(),
                              cookies=AsyncMock(return_value=[{"domain": ".douyin.com", "name": "anonymous", "value": "guest"}]))
    async def download(url, metadata, cookies, agent, work, progress):
        video = work / "video.mp4"
        video.write_bytes(b"downloaded guest video")
        progress(100, "完成")
        return video
    downloader = SimpleNamespace(download=AsyncMock(side_effect=download))
    reader = DouyinGuestReader(1, downloader)
    reader.poll_seconds = .001
    reader.metadata_wait_seconds = .01
    async def ensure():
        reader._context = context
    monkeypatch.setattr(reader, "_ensure_context", ensure)
    async def metadata(page, expected):
        return page.media
    monkeypatch.setattr(module, "_metadata_from_douyin_page", metadata)
    monkeypatch.setattr(module, "_requires_verification", AsyncMock(side_effect=lambda page: page.challenge))
    dismiss = AsyncMock(return_value=False)
    monkeypatch.setattr(module, "_dismiss_login_prompt", dismiss)
    return reader, page, context, downloader, dismiss


async def test_guest_uses_public_resources_before_touching_login_prompt(tmp_path, monkeypatch):
    reader, page, context, downloader, dismiss = await reader_fixture(tmp_path, monkeypatch)
    cookie = tmp_path / "cookies.txt"
    states = []
    try:
        evidence = await reader.acquire("https://v.douyin.com/short", cookie, on_state=lambda *state: states.append(state))
        assert evidence.media.video_source_policy == DOUYIN_GUEST_POLICY
        assert evidence.downloaded_video.read_bytes() == b"downloaded guest video"
        assert evidence.user_agent == "guest-agent" and "anonymous" in cookie.read_text()
        assert "sessionid" not in cookie.read_text()
        downloader.download.assert_awaited_once()
        dismiss.assert_not_awaited()
        page.close.assert_awaited_once()
        context.close.assert_not_awaited()
        assert any(state == "guest_downloading" for state, _ in states)
    finally:
        await reader.close()
    context.close.assert_awaited_once()


async def test_optional_login_prompt_is_closed_then_metadata_is_read_again(tmp_path, monkeypatch):
    reader, page, _, downloader, dismiss = await reader_fixture(tmp_path, monkeypatch, media=False)
    def close(_):
        page.media = MediaMetadata("123", "公开作品", source_urls=("https://cdn.test/video.mp4",))
        return True
    dismiss.side_effect = close
    states = []
    try:
        evidence = await reader.acquire(page.url, tmp_path / "cookies.txt", on_state=lambda *state: states.append(state))
        assert evidence is not None
        dismiss.assert_awaited_once()
        assert any("已关闭普通登录提示" in message for _, message in states)
        downloader.download.assert_awaited_once()
    finally:
        await reader.close()


async def test_verification_never_uses_login_close_or_download(tmp_path, monkeypatch):
    reader, page, _, downloader, dismiss = await reader_fixture(tmp_path, monkeypatch, challenge=True)
    states = []
    try:
        assert await reader.acquire(page.url, tmp_path / "cookies.txt", on_state=lambda *state: states.append(state)) is None
        dismiss.assert_not_awaited()
        downloader.download.assert_not_awaited()
        assert any("访客页要求验证" in message for _, message in states)
        page.close.assert_awaited_once()
    finally:
        await reader.close()


@pytest.mark.parametrize("reason", ["no_metadata", "wrong_work", "download_failed"])
async def test_unavailable_guest_source_returns_to_caller(tmp_path, monkeypatch, reason):
    reader, page, _, downloader, _ = await reader_fixture(tmp_path, monkeypatch, media=reason != "no_metadata")
    if reason == "wrong_work":
        page.media = MediaMetadata("other", "wrong", source_urls=("https://cdn.test/wrong.mp4",))
    elif reason == "download_failed":
        downloader.download.side_effect = DownloadFailedError("公开资源不可用")
    try:
        assert await reader.acquire(page.url, tmp_path / "cookies.txt") is None
        page.close.assert_awaited_once()
        if reason != "download_failed":
            downloader.download.assert_not_awaited()
    finally:
        await reader.close()


async def test_cancelled_guest_download_closes_page_and_does_not_return_fallback(tmp_path, monkeypatch):
    reader, page, _, downloader, _ = await reader_fixture(tmp_path, monkeypatch)
    started = asyncio.Event()
    stopped = asyncio.Event()
    async def hold(*_):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()
    downloader.download.side_effect = hold
    task = asyncio.create_task(reader.acquire(page.url, tmp_path / "cookies.txt"))
    try:
        await asyncio.wait_for(started.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert stopped.is_set()
        page.close.assert_awaited_once()
        assert not reader._lock.locked()
    finally:
        await reader.close()
