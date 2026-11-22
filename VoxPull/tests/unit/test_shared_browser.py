import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from voxpull.domain.errors import BrowserFailedError, DownloadFailedError, PlatformVerificationRequiredError
from voxpull.domain.models import BrowserEvidence, MediaMetadata, DOUYIN_INTERNAL_POLICY
from voxpull.infrastructure.browser import PlaywrightBrowser, _media_id_from_url
from voxpull.infrastructure.cookies import save_storage_state


def session():
    return {"domain": ".douyin.com", "name": "sessionid", "value": "test-session",
            "expires": -1, "path": "/", "secure": True, "httpOnly": True}


class Page:
    def __init__(self, context):
        self.context = context
        self.url = "about:blank"
        self.closed = False
        self.challenge = False
        self.on = lambda *_: None
        self.wait_for_timeout = AsyncMock()
        self.bring_to_front = AsyncMock()
        self.evaluate = AsyncMock(return_value="test-agent")

    def is_closed(self):
        return self.closed

    async def goto(self, url, **kwargs):
        self.url = url
        self.context.navigations.append(url)
        self.challenge = url in self.context.challenges


class Context:
    def __init__(self, challenges=(), cookies=None):
        self.challenges = set(challenges)
        self.navigations = []
        self.pages = [Page(self)]
        self.close = AsyncMock()
        self.cookies = AsyncMock(return_value=[session()] if cookies is None else cookies)
        self.storage_state = AsyncMock(side_effect=self.state)
        self.add_cookies = AsyncMock()
        self.request = SimpleNamespace(get=AsyncMock(side_effect=self.resolve))

    async def state(self):
        return {"cookies": await self.cookies(), "origins": [{"origin": "https://www.douyin.com", "localStorage": [{"name": "device", "value": "persisted-test"}]}]}

    async def resolve(self, url, **kwargs):
        return SimpleNamespace(url=url.replace("https://v.douyin.com/short", "https://www.douyin.com/video/123"), dispose=AsyncMock())


async def make_browser(tmp_path, monkeypatch, contexts):
    import voxpull.infrastructure.browser as module
    browser = PlaywrightBrowser(tmp_path / "profile", tmp_path / "state.json", 1)
    browser.verification_poll_seconds = .005
    browser.verification_wait_seconds = 1
    browser.share_fallback_wait_seconds = 0
    opened = []
    async def open_context(*, headless):
        opened.append(headless)
        browser._auth_context = contexts[min(len(opened)-1, len(contexts)-1)]
    async def metadata(page, expected):
        if not page.challenge and _media_id_from_url(page.url) == expected and not getattr(page, "unavailable", False):
            return MediaMetadata(expected, "test", source_urls=("https://cdn.test/video.mp4",))
    monkeypatch.setattr(browser, "_open_auth_context", open_context)
    monkeypatch.setattr(browser, "_window", AsyncMock())
    monkeypatch.setattr(module, "_metadata_from_douyin_page", metadata)
    monkeypatch.setattr(module, "_page_requires_auth_action", AsyncMock(side_effect=lambda page: page.challenge or "/login" in page.url))
    return browser, opened


async def until(predicate):
    async with asyncio.timeout(2):
        while not predicate():
            await asyncio.sleep(.005)


async def test_late_challenge_during_initial_loading_keeps_task_waiting(tmp_path, monkeypatch):
    url = 'https://www.douyin.com/video/123'
    context = Context()
    context.pages[0].unavailable = True
    browser, _ = await make_browser(tmp_path, monkeypatch, [context])
    browser.post_verification_grace_seconds = .5
    states = []
    task = asyncio.create_task(browser.acquire(url, cookie_file(tmp_path, 'late'),
                                               on_state=lambda state, _: states.append(state)))
    await until(lambda: context.navigations == [url])
    await asyncio.sleep(.02)
    assert not task.done()
    context.pages[0].challenge = True
    await until(lambda: 'verification_required' in states)
    assert not task.done()
    context.pages[0].unavailable = False
    context.pages[0].challenge = False
    assert (await task).media.id == '123'
    await browser.close()


async def test_explicit_idle_operation_confirms_media_before_reporting_passed(tmp_path, monkeypatch):
    from voxpull.infrastructure import slider_operation
    browser = PlaywrightBrowser(tmp_path/'profile', tmp_path/'auth/state.json', 1)
    context = Context()
    browser._page = context.pages[0]
    browser._pending_url = 'https://www.douyin.com/video/123'
    browser._status = 'verification_required'
    folder = tmp_path/'evidence'
    folder.mkdir()
    operation = AsyncMock(return_value={'status': 'performed', 'directory': str(folder)})
    monkeypatch.setattr(slider_operation, 'operate', operation)
    browser._inspect_page = AsyncMock(return_value=('ready', MediaMetadata('123', 'test')))
    assert (await browser.operate_current_slider(lambda: True))['status'] == 'manual'
    operation.assert_not_awaited()
    result = await browser.operate_current_slider(lambda: True, allow_idle=True)
    assert result['status'] == 'passed' and result['page_status'] == 'ready'
    assert json.loads((folder/'report.json').read_text())['status'] == 'passed'


async def test_rejected_operation_is_reported_while_task_keeps_waiting(tmp_path, monkeypatch):
    from voxpull.infrastructure import slider_operation
    browser = PlaywrightBrowser(tmp_path/'profile', tmp_path/'auth/state.json', 1)
    browser._page = Context().pages[0]
    browser._pending_url = 'https://www.douyin.com/video/123'
    browser._status = 'verification_required'
    folder = tmp_path/'evidence'
    folder.mkdir()
    monkeypatch.setattr(slider_operation, 'operate', AsyncMock(return_value={
        'status': 'performed', 'directory': str(folder), 'message': '已执行拖动'}))
    monkeypatch.setattr(slider_operation, 'operation_feedback',
                        AsyncMock(return_value='操作过快，请慢一点[5014][502]'))
    browser._inspect_page = AsyncMock(return_value=('verification_required', None))
    result = await browser.operate_current_slider(lambda: True, allow_idle=True)
    assert result['status'] == 'rejected'
    messages = []
    browser.verification_wait_seconds = .03
    browser.verification_poll_seconds = .005
    browser.share_fallback = AsyncMock()
    with pytest.raises(PlatformVerificationRequiredError):
        await browser._wait_for_access(lambda state, message: messages.append(message),
                                       share_url=browser._pending_url, cookie_file=tmp_path/'cookie')
    assert any('平台拒绝本次操作' in message and '任务继续等待' in message for message in messages)
    assert browser._operation_notice[0] == browser._pending_url
    await browser.close()


async def test_refresh_occurs_between_attempts_and_success_stops_retry(tmp_path, monkeypatch):
    from voxpull.infrastructure import slider_operation
    browser = PlaywrightBrowser(tmp_path/'profile', tmp_path/'state.json', 1)
    browser._page = Context().pages[0]
    browser._pending_url = 'https://www.douyin.com/video/123'
    browser._status = 'verification_required'
    browser._operate_current_slider_once = AsyncMock(side_effect=[
        {'status': 'rejected', 'message': '操作过快'}, {'status': 'passed', 'message': '通过'}])
    refresh = AsyncMock(return_value={'refreshed': True, 'message': '新图片已加载'})
    monkeypatch.setattr(slider_operation, 'refresh_slider', refresh)
    result = await browser.operate_current_slider(lambda: True, allow_idle=True, max_attempts=3)
    assert result['status'] == 'passed' and result['attempt_count'] == 2
    assert browser._operate_current_slider_once.await_count == 2
    refresh.assert_awaited_once()
    assert result['attempts'][0]['refresh']['refreshed']


@pytest.mark.parametrize('refreshed,attempts,refreshes', [(True, 3, 2), (False, 1, 1)])
async def test_refresh_retry_has_a_limit_and_stops_if_image_did_not_change(
        tmp_path, monkeypatch, refreshed, attempts, refreshes):
    from voxpull.infrastructure import slider_operation
    browser = PlaywrightBrowser(tmp_path/'profile', tmp_path/'state.json', 1)
    browser._page = Context().pages[0]
    browser._pending_url = 'https://www.douyin.com/video/123'
    browser._status = 'verification_required'
    browser._operate_current_slider_once = AsyncMock(return_value={'status': 'manual', 'message': '未检出'})
    refresh = AsyncMock(return_value={'refreshed': refreshed, 'message': '刷新结果'})
    monkeypatch.setattr(slider_operation, 'refresh_slider', refresh)
    result = await browser.operate_current_slider(lambda: True, allow_idle=True, max_attempts=3)
    assert result['attempt_count'] == attempts
    assert refresh.await_count == refreshes


async def test_cancelled_task_does_not_refresh_or_retry(tmp_path, monkeypatch):
    from voxpull.infrastructure import slider_operation
    browser = PlaywrightBrowser(tmp_path/'profile', tmp_path/'state.json', 1)
    browser._page = Context().pages[0]
    browser._pending_url = 'https://www.douyin.com/video/123'
    browser._status = 'verification_required'
    browser._operate_current_slider_once = AsyncMock(return_value={'status': 'manual', 'message': '已停止'})
    refresh = AsyncMock()
    monkeypatch.setattr(slider_operation, 'refresh_slider', refresh)
    result = await browser.operate_current_slider(lambda: False, allow_idle=True, max_attempts=3)
    assert result['attempt_count'] == 1
    refresh.assert_not_awaited()


async def test_guest_success_skips_an_existing_shared_verification_gate(tmp_path, monkeypatch):
    browser, opened = await make_browser(tmp_path, monkeypatch, [Context()])
    evidence = BrowserEvidence("https://www.douyin.com/video/456", "guest", cookie_file(tmp_path, "guest"), MediaMetadata("456", "public"))
    reader = SimpleNamespace(acquire=AsyncMock(return_value=evidence), close=AsyncMock())
    browser.guest_reader = reader
    browser._blocked = True
    browser._pending_url = "https://www.douyin.com/video/123"
    browser._status = "verification_required"
    browser.storage_state_path.write_text('{"saved":"unchanged"}')
    await browser._acquire_lock.acquire()
    try:
        assert await asyncio.wait_for(browser.acquire(evidence.final_url, evidence.cookie_file), 1) is evidence
        assert browser._blocked and browser._pending_url.endswith("123")
        assert browser._status == "verification_required"
        assert browser.storage_state_path.read_text() == '{"saved":"unchanged"}'
        assert not opened
    finally:
        browser._acquire_lock.release()
        await browser.close()
    reader.close.assert_awaited_once()


async def test_guest_unavailable_then_uses_original_login_flow(tmp_path, monkeypatch):
    browser, opened = await make_browser(tmp_path, monkeypatch, [Context()])
    browser.guest_reader = SimpleNamespace(acquire=AsyncMock(return_value=None), close=AsyncMock())
    states = []
    try:
        result = await browser.acquire("https://www.douyin.com/video/123", cookie_file(tmp_path, "fallback"), on_state=lambda *state: states.append(state))
        assert result.media.id == "123" and opened == [False]
        assert result.media.video_source_policy == DOUYIN_INTERNAL_POLICY
        assert any("访客页未取得可用资源" in message for _, message in states)
    finally:
        await browser.close()


def cookie_file(tmp_path, ident):
    folder = tmp_path / ident
    folder.mkdir()
    return folder / "cookies.txt"


async def test_two_tasks_and_verification_reuse_one_context_and_exact_work_page(tmp_path, monkeypatch):
    first = "https://www.douyin.com/video/123"
    context = Context([first])
    browser, opened = await make_browser(tmp_path, monkeypatch, [context])
    progress1, progress2 = [], []
    one = asyncio.create_task(browser.acquire("https://v.douyin.com/short", cookie_file(tmp_path, "one"), on_state=lambda *x: progress1.append(x)))
    await until(lambda: browser._blocked)
    original_page = browser._page
    two = asyncio.create_task(browser.acquire("https://www.douyin.com/video/456", cookie_file(tmp_path, "two"), on_state=lambda *x: progress2.append(x)))
    await until(lambda: browser._waiting == 1)
    assert await browser.auth_status() == "verification_required"
    assert await browser.start_auth("https://www.douyin.com/video/456") == "verification_required"
    assert await browser.complete_auth() == "verification_required"
    assert browser._page is original_page and context.navigations == [first]
    assert not browser.storage_state_path.exists()
    assert browser.auth_details()["waiting_jobs"] == 2
    original_page.challenge = False
    assert await browser.auth_status() == "ready"
    a, b = await asyncio.gather(one, two)
    assert (a.media.id, b.media.id) == ("123", "456")
    assert opened == [False] and context.navigations == [first, "https://www.douyin.com/video/456"]
    context.close.assert_not_awaited()
    assert any(state == "waiting_browser" for state, _ in progress2)
    assert progress1[-1][0] == progress2[-1][0] == ""
    assert json.loads(browser.storage_state_path.read_text())["origins"][0]["localStorage"][0]["value"] == "persisted-test"
    assert browser.auth_details()["waiting_jobs"] == 0


async def test_closed_verification_window_waits_for_explicit_reopen(tmp_path, monkeypatch):
    url = "https://www.douyin.com/video/123"
    old, new = Context([url]), Context([url])
    browser, opened = await make_browser(tmp_path, monkeypatch, [old, new])
    task = asyncio.create_task(browser.acquire(url, cookie_file(tmp_path, "job")))
    await until(lambda: browser._blocked)
    old.pages[0].closed = True
    old.pages = []
    await until(lambda: browser._status == "window_closed")
    assert not task.done() and opened == [False]
    assert await browser.start_auth() == "verification_required"
    assert new.navigations == [url] and opened == [False, False]
    new.pages[0].challenge = False
    assert (await task).media.id == "123"


async def test_share_copy_finishes_job_without_replacing_pending_verification(tmp_path, monkeypatch):
    url = "https://www.douyin.com/video/123"
    context = Context([url])
    browser, _ = await make_browser(tmp_path, monkeypatch, [context])
    cookies = cookie_file(tmp_path, "fallback")
    evidence = BrowserEvidence(url, "test-agent", cookies, MediaMetadata("123", "test"), cookies.with_suffix(".mp4"))
    browser.share_fallback = AsyncMock(return_value=evidence)
    try:
        assert await browser.acquire(url, cookies) is evidence
        browser.share_fallback.assert_awaited_once_with(url, cookies)
        assert browser._blocked and await browser.auth_status() == "verification_required"
        assert context.navigations == [url]
        assert not browser.storage_state_path.exists()
    finally:
        await browser.close()


async def test_unavailable_share_copy_returns_to_manual_verification(tmp_path, monkeypatch):
    url = "https://www.douyin.com/video/123"
    context = Context([url])
    browser, _ = await make_browser(tmp_path, monkeypatch, [context])
    browser.share_fallback = AsyncMock(return_value=None)
    states = []
    task = asyncio.create_task(browser.acquire(url, cookie_file(tmp_path, "fallback"),
                                               on_state=lambda *state: states.append(state)))
    try:
        await until(lambda: any("分享页未提供可下载视频" in message for _, message in states))
        assert not task.done()
        browser.share_fallback.assert_awaited_once()
        assert "剩余最多" in states[-1][1]
        context.pages[0].challenge = False
        assert (await task).media.video_source_policy == DOUYIN_INTERNAL_POLICY
    finally:
        await browser.close()


async def test_late_captcha_after_login_still_tries_share_fallback(tmp_path, monkeypatch):
    url = "https://www.douyin.com/video/123"
    context = Context([url])
    browser, _ = await make_browser(tmp_path, monkeypatch, [context])
    original_goto = context.pages[0].goto

    async def redirect_to_login(*args, **kwargs):
        await original_goto(*args, **kwargs)
        context.pages[0].url = "https://www.douyin.com/login/"

    context.pages[0].goto = redirect_to_login
    cookies = cookie_file(tmp_path, "late-captcha")
    evidence = BrowserEvidence(url, "test-agent", cookies, MediaMetadata("123", "test"))
    browser.share_fallback = AsyncMock(return_value=evidence)
    states = []
    task = asyncio.create_task(browser.acquire(url, cookies, on_state=lambda *state: states.append(state)))
    try:
        await until(lambda: any(state == "opening" for state, _ in states))
        browser.share_fallback.assert_not_awaited()
        context.pages[0].url = url
        assert await task is evidence
        browser.share_fallback.assert_awaited_once_with(url, cookies)
    finally:
        await browser.close()


async def test_unavailable_share_times_out_with_reason_without_repeated_attempts(tmp_path, monkeypatch):
    url = "https://www.douyin.com/video/123"
    browser, _ = await make_browser(tmp_path, monkeypatch, [Context([url])])
    browser.verification_wait_seconds = .03
    browser.share_fallback = AsyncMock(return_value=None)
    try:
        with pytest.raises(PlatformVerificationRequiredError, match="分享页未提供可下载视频，且人工验证等待已超时"):
            await browser.acquire(url, cookie_file(tmp_path, "unavailable"))
        browser.share_fallback.assert_awaited_once()
        assert browser._blocked
    finally:
        await browser.close()


async def test_manual_verification_within_grace_period_keeps_internal_source(tmp_path, monkeypatch):
    url = "https://www.douyin.com/video/123"
    context = Context([url])
    browser, _ = await make_browser(tmp_path, monkeypatch, [context])
    browser.share_fallback_wait_seconds = 1
    browser.share_fallback = AsyncMock(return_value=None)
    task = asyncio.create_task(browser.acquire(url, cookie_file(tmp_path, "manual")))
    try:
        await until(lambda: browser._blocked)
        context.pages[0].challenge = False
        assert (await task).media.video_source_policy == DOUYIN_INTERNAL_POLICY
        browser.share_fallback.assert_not_awaited()
    finally:
        await browser.close()


async def test_timeout_retains_page_and_blocks_next_navigation_until_verified(tmp_path, monkeypatch):
    first = "https://www.douyin.com/video/123"
    context = Context([first])
    browser, opened = await make_browser(tmp_path, monkeypatch, [context])
    browser.verification_wait_seconds = .01
    with pytest.raises(PlatformVerificationRequiredError):
        await browser.acquire(first, cookie_file(tmp_path, "one"))
    page = browser._page
    assert browser._blocked and not page.is_closed()
    browser.verification_wait_seconds = 1
    second = asyncio.create_task(browser.acquire("https://www.douyin.com/video/456", cookie_file(tmp_path, "two")))
    await asyncio.sleep(.02)
    assert context.navigations == [first] and not second.done()
    page.challenge = False
    assert (await second).media.id == "456" and opened == [False]


async def test_import_does_not_replace_a_waiting_verification_session(tmp_path, monkeypatch):
    url = "https://www.douyin.com/video/123"
    context = Context([url])
    browser, _ = await make_browser(tmp_path, monkeypatch, [context])
    save_storage_state(browser.storage_state_path, {"cookies": [session()], "origins": []})
    before = browser.storage_state_path.read_bytes()
    task = asyncio.create_task(browser.acquire(url, cookie_file(tmp_path, "job")))
    await until(lambda: browser._blocked)
    with pytest.raises(BrowserFailedError, match="不替换"):
        await browser.import_chrome_cookies()
    assert browser.storage_state_path.read_bytes() == before
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not browser._active and browser._waiting == 0


async def test_interrupting_verification_releases_job_lock_and_keeps_login_page(tmp_path, monkeypatch):
    url = "https://www.douyin.com/video/123"
    context = Context([url])
    browser, _ = await make_browser(tmp_path, monkeypatch, [context])
    task = asyncio.create_task(browser.acquire(url, cookie_file(tmp_path, "paused")))
    try:
        await until(lambda: browser._blocked)
        page = browser._page
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not browser._active and not browser._acquire_lock.locked()
        assert browser._blocked and not page.is_closed()
        page.challenge = False
        assert await browser.auth_status() == "ready"
        result = await browser.acquire("https://www.douyin.com/video/456", cookie_file(tmp_path, "next"))
        assert result.media.id == "456"
    finally:
        await browser.close()


async def test_missing_or_saved_state_is_not_reported_as_verified(tmp_path, monkeypatch):
    browser, _ = await make_browser(tmp_path, monkeypatch, [Context()])
    assert await browser.auth_status() == "missing"
    save_storage_state(browser.storage_state_path, {"cookies": [session()], "origins": []})
    assert await browser.auth_status() == "saved"
    assert await browser.start_auth("https://v.douyin.com/short") == "ready"
    assert browser._pending_url == "https://www.douyin.com/video/123"


async def test_successful_login_after_manual_action_keeps_context_open(tmp_path, monkeypatch):
    context = Context(cookies=[])
    browser, opened = await make_browser(tmp_path, monkeypatch, [context])
    assert await browser.start_auth() == "opening"
    assert await browser.auth_status() == "opening"
    context.cookies.return_value = [session()]
    assert await browser.auth_status() == "ready"
    context.close.assert_not_awaited()
    assert opened == [False]


async def test_unavailable_work_after_verification_does_not_hold_other_works_forever(tmp_path, monkeypatch):
    url = "https://www.douyin.com/video/123"
    context = Context([url])
    browser, _ = await make_browser(tmp_path, monkeypatch, [context])
    browser.post_verification_grace_seconds = .01
    task = asyncio.create_task(browser.acquire(url, cookie_file(tmp_path, "job")))
    await until(lambda: browser._blocked)
    browser._page.challenge = False
    browser._page.unavailable = True
    with pytest.raises(DownloadFailedError, match="其他作品可继续"):
        await task
    assert not browser._blocked


async def test_login_redirect_returns_to_original_work_in_same_context(tmp_path, monkeypatch):
    url = "https://www.douyin.com/video/123"
    context = Context([url])
    browser, opened = await make_browser(tmp_path, monkeypatch, [context])
    task = asyncio.create_task(browser.acquire(url, cookie_file(tmp_path, "job")))
    await until(lambda: browser._blocked)
    browser._page.url = "https://www.douyin.com/login/"
    assert await browser.auth_status() == "opening"
    assert browser._return_after_login
    browser._page.challenge = False
    browser._page.url = "https://www.douyin.com/"
    context.challenges.clear()
    result = await task
    assert result.media.id == "123" and context.navigations == [url, url]
    assert opened == [False]


async def test_standalone_verification_auto_saves_without_ui_polling(tmp_path, monkeypatch):
    url = "https://www.douyin.com/video/123"
    context = Context([url])
    browser, _ = await make_browser(tmp_path, monkeypatch, [context])
    assert await browser.start_auth(url) == "verification_required"
    browser._page.challenge = False
    await until(lambda: browser._status == "ready")
    assert not browser._blocked and browser.storage_state_path.exists()
    context.close.assert_not_awaited()
    await browser.close()


async def test_reopening_profile_does_not_overwrite_newer_verified_cookies(tmp_path, monkeypatch):
    import os
    import voxpull.infrastructure.browser as module
    browser = PlaywrightBrowser(tmp_path / "profile", tmp_path / "state.json", 1)
    save_storage_state(browser.storage_state_path, {"cookies": [session()], "origins": []})
    cookies = browser.profile_dir / "Default/Cookies"
    cookies.parent.mkdir(parents=True)
    cookies.write_bytes(b"test database marker")
    state_time = browser.storage_state_path.stat().st_mtime_ns
    os.utime(cookies, ns=(state_time + 1_000_000_000, state_time + 1_000_000_000))
    context = Context()
    playwright = SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=AsyncMock(return_value=context)))
    monkeypatch.setattr(module, 'async_playwright', lambda: SimpleNamespace(start=AsyncMock(return_value=playwright)))
    await browser._open_auth_context()
    context.add_cookies.assert_not_awaited()
    # An explicit later Chrome import remains eligible to seed the profile.
    os.utime(browser.storage_state_path, ns=(state_time + 2_000_000_000, state_time + 2_000_000_000))
    await browser._open_auth_context()
    context.add_cookies.assert_awaited_once()


async def test_opening_verification_restores_existing_page_without_reloading(tmp_path, monkeypatch):
    context = Context()
    browser, _ = await make_browser(tmp_path, monkeypatch, [context])
    url = "https://www.douyin.com/video/123"
    await browser.acquire(url, cookie_file(tmp_path, "job"))
    context.navigations.clear()
    browser._window.reset_mock()
    assert await browser.start_auth() == "ready"
    assert context.navigations == []
    assert browser._page.url == url
    browser._window.assert_any_await("normal")


async def test_window_is_visible_before_slow_or_failed_first_navigation(tmp_path, monkeypatch):
    context = Context()
    browser, _ = await make_browser(tmp_path, monkeypatch, [context])

    async def failed_navigation(*args, **kwargs):
        browser._window.assert_awaited_with("normal")
        raise TimeoutError("network unavailable")

    context.pages[0].goto = failed_navigation
    with pytest.raises(BrowserFailedError):
        await browser.start_auth()


async def test_docker_download_keeps_browser_visible(tmp_path, monkeypatch):
    monkeypatch.setenv("VOXPULL_BROWSER_CONSOLE_URL", "http://127.0.0.1:6080/vnc.html")
    browser, _ = await make_browser(tmp_path, monkeypatch, [Context()])
    assert (await browser.acquire("https://www.douyin.com/video/123", cookie_file(tmp_path, "job"))).media.id == "123"
    assert not any(call.args == ("minimized",) for call in browser._window.await_args_list)
