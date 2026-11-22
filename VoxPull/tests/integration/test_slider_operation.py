import base64
from unittest.mock import AsyncMock

import httpx
import pytest
from playwright.async_api import async_playwright

from test_api import make_settings
from voxpull.app import create_app
from voxpull.domain.models import Job, JobStage, JobStatus
from voxpull.infrastructure.slider_operation import (
    drag_plan, inspect_layout, operate, operation_feedback, piece_alpha_bounds,
    motion_schedule, refresh_slider,
)
from voxpull.infrastructure.browser import _page_requires_auth_action


@pytest.fixture
async def owned_page():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content('<iframe style="width:500px;height:400px;border:0"></iframe>')
        frame = page.frames[1]
        await frame.set_content('''
        <div id="scene" style="position:relative;width:300px;height:150px;background:#ccc">
          <div id="piece" style="position:absolute;left:10px;top:20px;width:40px;height:40px;background:red"></div>
        </div>
        <div id="track" style="position:relative;width:300px;height:40px;background:#eee">
          <div role="slider" aria-label="拖动滑块"
            style="position:absolute;width:40px;height:40px;background:blue"></div>
        </div>
        <script>window.released = 0;
          document.querySelector('[role=slider]').addEventListener('pointerdown', e => {
            e.target.setPointerCapture(e.pointerId);
          });
          document.addEventListener('pointerup', () => window.released++);
        </script>''')
        try:
            yield page, frame
        finally:
            await browser.close()


async def test_operates_existing_page_inside_iframe_and_preserves_session(owned_page, tmp_path):
    page, frame = owned_page
    async def predict(image):
        assert base64.b64decode(image).startswith(b'\x89PNG')
        return {"detected": True, "box": [140, 20, 180, 60], "confidence": .9}
    result = await operate(page, predict, lambda: True, tmp_path)
    assert result['status'] == 'performed'
    assert result['drag_duration_seconds'] >= result['trajectory_plan']['总用时（毫秒）'] / 1000 - .02
    assert result['motion_algorithm'] == '分阶段连续运动-v3-首峰增强'
    assert result['drag_plan']['end'] == [result['motion_schedule'][-1]['x'], result['motion_schedule'][-1]['y']]
    assert await frame.evaluate('window.released') == 1
    assert len(page.context.pages) == 1 and page.url == 'about:blank'
    assert list(tmp_path.glob('*/report.json')) and list(tmp_path.glob('*/input.png'))


async def test_layout_diagnostics_reads_iframe_without_input_values(owned_page):
    page, frame = owned_page
    await frame.locator('body').evaluate("el => el.insertAdjacentHTML('beforeend', '<input value=private-value>')")
    layout = await inspect_layout(page)
    assert len(layout['frames']) == 2
    assert any(el['id'] == 'scene' for el in layout['frames'][1]['elements']) is False
    assert any(el['role'] == 'slider' for el in layout['frames'][1]['elements'])
    assert 'private-value' not in str(layout)


async def test_observed_iframe_layout_with_scaled_coordinates(owned_page, tmp_path):
    page, frame = owned_page
    await page.locator('iframe').evaluate("el => { el.style.transform='scale(.75)'; el.style.transformOrigin='top left'; }")
    image = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="340" height="212"%3E%3Crect width="340" height="212" fill="gray"/%3E%3C/svg%3E'
    piece = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="68" height="68"%3E%3Crect width="68" height="68" fill="red"/%3E%3C/svg%3E'
    await frame.set_content(f'''
        <div id="captcha_container"><div class="vc-captcha-verify">
          <div class="captcha_verify_img--wrapper" style="position:relative;width:340px;height:212px">
            <img id="captcha_verify_image" src='{image}' style="width:340px;height:212px">
            <div class="dragger-item" style="position:absolute;left:0;top:20px">
              <img id="captcha-verify_img_slide" src='{piece}' style="width:68px;height:68px">
            </div>
          </div>
          <div class="captcha-slider"><div class="captcha-slider-box"
            style="position:relative;width:340px;height:44px">
            <div class="dragger-item" style="position:absolute;left:0;top:0;width:64px;height:40px;background:blue">
              <div class="captcha-slider-btn">→</div>
            </div>
          </div></div>
        </div></div>
        <script>window.released=0;document.addEventListener('pointerup',()=>window.released++);</script>
    ''')
    assert await _page_requires_auth_action(page)
    prediction = {'detected': True, 'box': [112.5, 15, 150, 60],
                  'source_box': [7.5, 15, 45, 60], 'confidence': .9}
    result = await operate(page, AsyncMock(return_value=prediction), lambda: True, tmp_path)
    assert result['status'] == 'performed', result
    assert result['viewport_scale'] == pytest.approx(.75)
    assert result['drag_plan']['source_offset_css_px'] == pytest.approx(7.5)
    assert result['drag_plan']['delta_css_px'] == pytest.approx(105 / 204 * 207)
    assert await frame.evaluate('window.released') == 1
    await page.locator('iframe').evaluate("el => el.style.display='none'")
    assert not await _page_requires_auth_action(page)


async def test_feedback_reads_visible_rejection_in_iframe(owned_page):
    page, frame = owned_page
    await frame.set_content('<div class="vc-captcha-verify">请完成操作<p>操作过快，请慢一点[5014]</p></div>')
    assert await operation_feedback(page) == '操作过快，请慢一点[5014]'
    await frame.locator('p').evaluate("el => el.style.display='none'")
    assert await operation_feedback(page) == ''


async def test_single_target_uses_visible_piece_alpha_padding(owned_page, tmp_path):
    page, frame = owned_page
    image = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="80" height="80"%3E%3Crect x="10" y="8" width="50" height="60" fill="red"/%3E%3C/svg%3E'
    await frame.locator('#piece').evaluate("(el,src) => { const img=document.createElement('img'); img.id=el.id; img.src=src; img.style.cssText=el.style.cssText; el.replaceWith(img); }", image)
    await frame.locator('#piece').evaluate('img => img.decode()')
    alpha = await piece_alpha_bounds(frame.locator('#piece'))
    assert alpha['left'] == 10 and alpha['width'] == 80
    prediction = {'detected': True, 'box': [140, 20, 180, 60], 'confidence': .937}
    result = await operate(page, AsyncMock(return_value=prediction), lambda: True, tmp_path)
    assert result['status'] == 'performed', result
    assert result['prediction']['source_origin'] == 'visible_piece_alpha'
    assert result['drag_plan']['source_offset_css_px'] == pytest.approx(5)


def test_source_only_detection_cannot_trigger_a_zero_distance_drag():
    boxes = {name: {'x': 0, 'y': 0, 'width': 40, 'height': 40}
             for name in ['image', 'piece', 'handle', 'track']}
    boxes['image']['width'] = 300
    with pytest.raises(ValueError, match='起始图块'):
        drag_plan(boxes, {'detected': True, 'box': [5, 0, 35, 40],
                         'source_box': [5, 0, 35, 40], 'confidence': .9}, 300, 260)


@pytest.mark.parametrize('changed', ['image', 'task'])
async def test_changed_image_or_cancelled_task_never_drags(owned_page, tmp_path, changed):
    page, frame = owned_page
    active = True
    async def predict(image):
        nonlocal active
        if changed == 'image':
            await frame.locator('#scene').evaluate("el => el.style.background = 'green'")
        else:
            active = False
        return {"detected": True, "box": [140, 20, 180, 60], "confidence": .9}
    result = await operate(page, predict, lambda: active, tmp_path)
    assert result['status'] == 'manual'
    assert await frame.evaluate('window.released') == 0


async def test_unsupported_layout_does_not_invoke_model(owned_page, tmp_path):
    page, frame = owned_page
    await frame.locator('#piece').evaluate("el => el.removeAttribute('id')")
    predict = AsyncMock()
    result = await operate(page, predict, lambda: True, tmp_path)
    assert result['status'] == 'manual'
    predict.assert_not_awaited()


@pytest.mark.parametrize('target,confidence', [(1000, .9), (100, .1), (float('nan'), .9)])
def test_invalid_predictions_cannot_become_mouse_coordinates(target, confidence):
    boxes = {name: {'x': 0, 'y': 0, 'width': 40, 'height': 40}
             for name in ['image', 'piece', 'handle', 'track']}
    boxes['image']['width'] = 300
    with pytest.raises(ValueError):
        drag_plan(boxes, {'detected': True, 'box': [target, 0, 200, 40],
                         'confidence': confidence}, 300, 260)


async def test_api_allows_only_waiting_job_and_local_origin(tmp_path):
    app = create_app(make_settings(tmp_path))
    container = app.state.container
    ident = 'a' * 32
    container.job_service.repository.add(Job(
        ident, 'https://www.douyin.com/video/123', 'zh', status=JobStatus.RUNNING,
        stage=JobStage.ACQUIRING_COOKIE, metadata={'auth_status': 'verification_required'},
    ))
    container.browser.operate_current_slider = AsyncMock(return_value={'status': 'performed'})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
        payload = {'job_id': ident}
        assert (await client.post('/api/auth/douyin/operate', json=payload,
                                  headers={'Origin': 'https://outside.test'})).status_code == 403
        assert (await client.post('/api/auth/douyin/operate', json={'job_id': 'b'*32})).status_code == 409
        response = await client.post('/api/auth/douyin/operate', json=payload)
        assert response.json() == {'status': 'performed'}
        waiting = container.browser.operate_current_slider.call_args.args[0]
        assert waiting()
        container.job_service.repository.update(ident, status=JobStatus.PAUSED)
        assert not waiting()
        assert (await client.post('/api/auth/douyin/operate', json=payload)).status_code == 409


async def test_explicit_test_rejects_other_targets_and_busy_browser(tmp_path):
    app = create_app(make_settings(tmp_path))
    browser = app.state.container.browser
    target = 'https://www.douyin.com/video/123'
    browser._pending_url = target
    browser.auth_status = AsyncMock(return_value='verification_required')
    browser.operate_current_slider = AsyncMock(return_value={'status': 'passed'})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
        endpoint = '/api/auth/douyin/operate-current'
        assert (await client.post(endpoint, json={'target_url': target},
                                  headers={'Origin': 'https://outside.test'})).status_code == 403
        assert (await client.post(endpoint, json={'target_url': target+'4'})).status_code == 409
        browser._active = True
        assert (await client.post(endpoint, json={'target_url': target})).status_code == 409
        browser._active = False
        assert (await client.post(endpoint, json={'target_url': target})).json() == {'status': 'passed'}
        assert browser.operate_current_slider.call_args.kwargs == {'allow_idle': True, 'max_attempts': 3}
        guard = browser.operate_current_slider.call_args.args[0]
        assert guard()
        browser._pending_url = target+'4'
        assert not guard()


def test_random_motion_varies_velocity_but_keeps_bounds_and_endpoint():
    points = motion_schedule(42)
    assert points == motion_schedule(42)
    assert points != motion_schedule(43)
    assert points[-1]['progress'] == 1 and 1.19582 <= points[-1]['time'] <= 1.937051
    previous_position, previous_time = 0, -1
    velocities = []
    for point in points:
        assert previous_position - 1e-12 <= point['progress'] <= 1 + 1e-12
        assert previous_time < point['time']
        if previous_time >= 0:
            velocities.append((point['progress']-previous_position)/(point['time']-previous_time))
        previous_position, previous_time = point['progress'], point['time']
    positive = [velocity for velocity in velocities if velocity > 1e-8]
    assert max(positive) > 2 * min(positive)


async def test_refresh_clicks_once_and_requires_a_replacement_image(owned_page):
    page, frame = owned_page
    await frame.locator('body').evaluate("""el => {
        const wrapper=document.createElement('div'); wrapper.id='challenge';
        el.append(wrapper);
        wrapper.innerHTML='<button data-action="refresh">刷新</button>';
        window.refreshes=0;
        wrapper.querySelector('button').onclick=()=> {
            window.refreshes++;
            document.querySelector('#scene').style.background='green';
        };
    }""")
    assert (await refresh_slider(page, lambda: False))['refreshed'] is False
    assert await frame.evaluate('window.refreshes') == 0
    result = await refresh_slider(page, lambda: True)
    assert result['refreshed'] is True
    assert await frame.evaluate('window.refreshes') == 1
