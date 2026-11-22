import pytest
from playwright.async_api import Error, async_playwright

from voxpull.infrastructure.douyin_guest import _dismiss_login_prompt


@pytest.fixture
async def guest_page():
    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(headless=True)
        except Error as exc:
            pytest.skip(f"Local Chromium unavailable: {type(exc).__name__}")
        page = await browser.new_page(viewport={"width": 1280, "height": 820})
        try:
            yield page
        finally:
            await browser.close()


def dialog(control):
    return f'''<div role="dialog" id="login-modal"
      style="position:absolute;left:200px;top:100px;width:600px;height:400px;background:white">
      <h2>Log in to Douyin</h2>{control}<input placeholder="phone">
      </div>'''


@pytest.mark.parametrize("kind", ["named_button", "unlabeled_svg", "iframe"])
async def test_only_visible_login_dialog_close_is_clicked(guest_page, kind):
    if kind == "unlabeled_svg":
        control = '''<div style="position:absolute;right:20px;top:20px;width:24px;height:24px"
            onclick="document.querySelector('#login-modal').remove()">
            <svg width="24" height="24"><path d="M2 2L22 22M2 22L22 2" stroke="black"/></svg></div>'''
    else:
        control = '''<button aria-label="关闭" style="position:absolute;right:20px;top:20px;width:24px;height:24px"
            onclick="document.querySelector('#login-modal').remove()">×</button>'''
    if kind == "iframe":
        await guest_page.set_content('<iframe style="border:0;width:100%;height:780px"></iframe>')
        await guest_page.frames[1].set_content(dialog(control))
    else:
        await guest_page.set_content(dialog(control))
    assert await _dismiss_login_prompt(guest_page)
    for frame in guest_page.frames:
        assert await frame.locator('#login-modal').count() == 0


async def test_verification_blocks_ordinary_close_even_when_login_dialog_exists(guest_page):
    await guest_page.set_content(dialog('''<button aria-label="关闭" class="close"
        style="position:absolute;right:20px;top:20px" onclick="this.parentElement.remove()">×</button>''')
        + '<div id="captcha" style="width:300px;height:200px">请完成验证</div>')
    assert not await _dismiss_login_prompt(guest_page)
    assert await guest_page.locator('#login-modal').is_visible()


async def test_unrelated_close_button_is_not_clicked(guest_page):
    await guest_page.set_content('''<div role="dialog" style="width:600px;height:400px">
        <h2>确认删除</h2><button class="close" onclick="window.clicked=true">×</button></div>''')
    assert not await _dismiss_login_prompt(guest_page)
    assert not await guest_page.evaluate('Boolean(window.clicked)')
