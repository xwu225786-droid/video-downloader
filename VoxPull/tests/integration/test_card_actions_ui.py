import asyncio
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.async_api import async_playwright, expect


@pytest.fixture
def static_app():
    root = Path(__file__).resolve().parents[2]/'src/voxpull/web'
    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith('/static/'):
                self.path = self.path.removeprefix('/static')
            super().do_GET()
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.mark.parametrize('width', [1280, 390])
async def test_card_actions_order_extraction_retry_and_summary_isolation(static_app, width, tmp_path):
    ids = ['a'*32, 'b'*32, 'c'*32, 'd'*32]
    jobs = {}
    for index, ident in enumerate(ids):
        image = index == 2
        jobs[ident] = {'id': ident, 'status': 'completed', 'stage': 'completed', 'progress': 100,
            'created_at': '2026-11-22T00:00:00Z', 'message': '已完成', 'error': None,
            'result': {'media': {'id': str(index), 'kind': 'images' if image else 'video',
                'title': f'测试作品{index+1}', 'saved': True, 'filename': '视频.mp4',
                'absolute_path': '/mock/视频.mp4', 'title_path': '/mock/标题.txt',
                'description': '图文正文' if image else '', 'assets': [], 'asset_count': 0,
                'cover_url': f'/api/jobs/{ident}/cover', 'video_url': f'/api/jobs/{ident}/video'},
                'transcript': {'text': '作品2字幕', 'segments': [], 'detected_language': 'zh'} if index == 1 else None}}
    jobs[ids[3]].update(status='running', stage='transcribing', progress=60,
                        subtitle_state='generating', summary_state='waiting')
    extraction_calls, summary_calls = [], []
    extraction_options = []
    extraction_running = set()
    errors = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': width, 'height': 1000})
        page.set_default_timeout(5000)
        page.on('pageerror', lambda error: errors.append(str(error)))
        async def api_route(route):
            path = urlparse(route.request.url).path
            data = {}
            if path.endswith('/cover'):
                return await route.fulfill(content_type='image/svg+xml', body='<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect width="320" height="180" fill="#dbeafe"/></svg>')
            if path.endswith('/video'):
                return await route.fulfill(status=204, body='')
            if path == '/api/jobs/capabilities':
                data = {'extract_txt': True, 'material_folders': True}
            elif path == '/api/summary/config':
                data = {'configured': True, 'model': 'mock-model', 'base_url': 'http://mock.test'}
            elif path == '/api/material-tags':
                data = {'tags': [], 'assignments': {}}
            elif path == '/api/system':
                data = {key: {'ready': True, 'detail': 'ready'} for key in
                        ['python','playwright','chromium','cookie','yt_dlp','ffmpeg']}
                data.update(video_storage_path='/mock', image_storage_path='/mock')
            elif path.endswith('/status') and not path.startswith('/api/jobs/'):
                data = {'status': 'ready', 'session_shared': True}
            elif path.startswith('/api/jobs/'):
                ident = path.split('/')[3]
                if path.endswith('/transcript/status'):
                    state = 'running' if ident in extraction_running else 'completed' if jobs[ident]['result']['transcript'] else 'idle'
                    return await route.fulfill(json={'state': state,
                        'progress': 35 if ident in extraction_running else None,
                        'message': '正在识别语音', 'elapsed_seconds': 125})
                if path.endswith('/transcript'):
                    extraction_calls.append(ident)
                    extraction_options.append(parse_qs(urlparse(route.request.url).query).get('regenerate') == ['true'])
                    extraction_running.add(ident)
                    await asyncio.sleep(2 if len(extraction_calls) == 1 else .2)
                    extraction_running.discard(ident)
                    if len(extraction_calls) == 1:
                        return await route.fulfill(status=502, json={'message': '模拟提取失败'})
                    jobs[ident]['result']['transcript'] = {'text': '作品1新字幕', 'segments': [], 'detected_language': 'zh'}
                if path.endswith('/summary'):
                    summary_calls.append((ident, route.request.post_data_json))
                    await asyncio.sleep(.4)
                    summary = {'markdown': f'## 作品{ids.index(ident)+1}模拟总结', 'model': 'mock-model',
                        'source_text': route.request.post_data_json['transcript_text'],
                        'style': 'brief', 'generated_at': '2026-11-22T04:00:00Z'}
                    jobs[ident]['summary'] = summary
                    return await route.fulfill(json=summary)
                data = jobs.get(ident, {})
            await route.fulfill(json=data)
        await page.route('**/api/**', api_route)
        await page.add_init_script("localStorage.setItem('media.queue.sources.v1', "
                                   + json.dumps(json.dumps([{'type':'single','id':ident} for ident in ids])) + ");")
        await page.goto(static_app)
        async def open_card(index):
            await page.locator('.batch-item').filter(has_text=f'测试作品{index+1}').get_by_role('button', name='查看结果', exact=True).click()
            await expect(page.locator('#batch-file-actions')).to_be_visible()
        await open_card(0)
        footer = page.locator('#batch-file-actions')
        tabs = page.get_by_role('tablist', name='转写结果视图')
        dialog = page.locator('#card-regenerate-dialog')
        extract = page.locator('#transcript-generate')
        feedback = page.locator('#transcript-action-feedback')
        generate = page.locator('#summary-generate')
        regenerate = page.locator('#summary-regenerate')
        assert await footer.locator('button').all_text_contents() == ['打开文件夹']
        await expect(tabs).to_be_visible()
        await expect(page.locator('#result-view-panel')).to_be_hidden()
        await expect(extract).to_be_hidden()
        await tabs.get_by_role('tab', name='字幕', exact=True).click()
        await expect(extract).to_be_visible()
        await tabs.get_by_role('tab', name='字幕', exact=True).click()
        await expect(page.locator('#result-view-panel')).to_be_hidden()
        await tabs.get_by_role('tab', name='字幕', exact=True).click()
        await expect(extract).to_be_visible()
        await expect(page.locator('#transcript-editor')).to_be_hidden()
        empty_box = await page.locator('#transcript-empty').bounding_box()
        button_box = await extract.bounding_box()
        assert abs(button_box['x'] + button_box['width']/2 - empty_box['x'] - empty_box['width']/2) < 2
        await tabs.get_by_role('tab', name='AI 总结', exact=True).click()
        await expect(generate).to_be_visible()
        await expect(generate).to_be_disabled()
        await tabs.get_by_role('tab', name='字幕', exact=True).click()
        automatic = page.locator('#auto-summary-toggle')
        await automatic.click()
        await expect(dialog).to_contain_text('开启自动生成AI总结')
        await expect(automatic).to_have_attribute('aria-checked', 'false')
        await dialog.get_by_role('button', name='取消', exact=True).click()
        await automatic.click()
        await dialog.get_by_role('button', name='确认开启', exact=True).click()
        await expect(automatic).to_have_attribute('aria-checked', 'true')
        await automatic.click()
        assert summary_calls == []
        await extract.click()
        await expect(extract).to_have_text('提取中…')
        await expect(extract).to_be_disabled()
        await expect(feedback).to_contain_text('35%')
        await expect(feedback).to_contain_text('2分5秒')
        await expect(feedback).to_contain_text('模拟提取失败')
        await extract.click()
        await expect(page.locator('#transcript-editor')).to_have_value('作品1新字幕')
        await expect(extract).to_be_hidden()
        card = page.locator(f'.batch-item[data-job-id="{ids[0]}"]')
        await expect(card.locator('.card-subtitle-completed')).to_be_visible()
        assert await card.locator('.card-subtitle-completed').evaluate("node => getComputedStyle(node, '::before').content") in ('none', 'normal', '""')
        editor_box = await page.locator('#transcript-editor').bounding_box()
        tabs_box = await tabs.bounding_box()
        assert tabs_box['y'] + tabs_box['height'] <= editor_box['y']
        assert (await page.locator('#copy-text').bounding_box())['y'] >= editor_box['y'] + editor_box['height']
        await tabs.get_by_role('tab', name='AI 总结', exact=True).click()
        await generate.click()
        await expect(dialog).to_contain_text('是否使用当前文案生成AI总结')
        assert summary_calls == []
        await dialog.get_by_role('button', name='取消', exact=True).click()
        assert summary_calls == []
        await generate.click()
        await dialog.get_by_role('button', name='开始生成', exact=True).click()
        await expect(page.locator('#summary-progress')).to_be_visible()
        await tabs.get_by_role('tab', name='字幕', exact=True).click()
        await expect(page.locator('#transcript-editor')).to_be_visible()
        await expect(page.locator('#summary-markdown')).to_contain_text('作品1模拟总结')
        await tabs.get_by_role('tab', name='AI 总结', exact=True).click()
        await expect(card.locator('.card-summary-completed')).to_be_visible()
        await regenerate.click()
        await dialog.get_by_role('button', name='取消', exact=True).click()
        await tabs.get_by_role('tab', name='字幕', exact=True).click()
        await page.locator('#transcript-regenerate').click()
        await dialog.get_by_role('button', name='取消', exact=True).click()
        assert len(extraction_calls) == 2 and len(summary_calls) == 1
        await open_card(1)
        await tabs.get_by_role('tab', name='AI 总结', exact=True).click()
        await generate.click()
        await dialog.get_by_role('button', name='开始生成', exact=True).click()
        await expect(page.locator('#summary-markdown')).to_contain_text('作品2模拟总结')
        await open_card(0)
        await tabs.get_by_role('tab', name='AI 总结', exact=True).click()
        await expect(page.locator('#summary-markdown')).to_contain_text('作品1模拟总结')
        assert len(summary_calls) == 2
        await open_card(2)
        await expect(page.locator('#transcript-regenerate')).to_be_hidden()
        await tabs.get_by_role('tab', name='AI 总结', exact=True).click()
        await generate.click()
        await dialog.get_by_role('button', name='开始生成', exact=True).click()
        await expect(page.locator('#summary-markdown')).to_contain_text('作品3模拟总结')
        assert summary_calls[-1][1]['transcript_text'] == '图文正文'
        await regenerate.click()
        await dialog.get_by_role('button', name='重新生成', exact=True).click()
        await expect(page.locator('#summary-progress')).to_be_visible()
        await expect(page.locator('#summary-markdown')).to_be_visible()
        assert len(summary_calls) == 4
        jobs[ids[0]]['result']['transcript'] = None
        extraction_running.add(ids[0])
        await page.reload()
        await open_card(0)
        await expect(page.locator('#result-view-panel')).to_be_hidden()
        await tabs.get_by_role('tab', name='字幕', exact=True).click()
        await expect(extract).to_have_text('提取中…')
        await expect(feedback).to_contain_text('35%')
        jobs[ids[0]]['result']['transcript'] = {'text':'刷新后完成字幕', 'segments':[], 'detected_language':'zh'}
        extraction_running.discard(ids[0])
        await expect(page.locator('#transcript-editor')).to_have_value('刷新后完成字幕')
        await tabs.get_by_role('tab', name='AI 总结', exact=True).click()
        await expect(page.locator('#summary-markdown')).to_contain_text('作品1模拟总结')
        assert len(extraction_calls) == 2
        await open_card(3)
        progressive = page.locator(f'.batch-item[data-job-id="{ids[3]}"]')
        await expect(progressive.locator('.card-subtitle-completed')).to_have_text('字幕生成中')
        await expect(progressive.locator('.card-summary-completed')).to_have_text('AI总结等待字幕')
        await expect(page.locator('#batch-video-player')).to_be_visible()
        await page.locator('#batch-video-player').evaluate("video => { video.dataset.reloads = '0'; const load = video.load.bind(video); video.load = () => { video.dataset.reloads = String(Number(video.dataset.reloads) + 1); load(); }; }")
        await expect(extract).to_be_disabled()
        await tabs.get_by_role('tab', name='AI 总结', exact=True).click()
        await expect(generate).to_be_disabled()
        jobs[ids[3]]['result']['transcript'] = {'text':'处理中字幕', 'segments':[], 'detected_language':'zh'}
        jobs[ids[3]].update(subtitle_state='completed', summary_state='generating', progress=99)
        await expect(page.locator('#summary-progress')).to_be_visible()
        await expect(page.locator('#summary-cancel')).to_be_hidden()
        expected_summaries = 4
        if width == 390:
            jobs[ids[3]].update(status='completed', stage='completed', progress=100, summary_state='failed')
            await expect(page.locator('#summary-error')).to_be_visible()
            await page.locator('#summary-retry').click()
            await dialog.get_by_role('button', name='开始生成', exact=True).click()
            await expect(page.locator('#summary-markdown')).to_contain_text('作品4模拟总结')
            expected_summaries = 5
        else:
            jobs[ids[3]]['summary'] = {'markdown':'自动总结完成', 'source_text':'处理中字幕',
                'style':'brief', 'model':'mock-model', 'generated_at':'2026-11-22T04:00:00Z'}
            jobs[ids[3]].update(status='completed', stage='completed', progress=100, summary_state='completed')
            await expect(page.locator('#summary-markdown')).to_have_text('自动总结完成')
        await expect(page.locator('#batch-video-player')).to_have_attribute('data-reloads', '0')
        assert len(summary_calls) == expected_summaries
        await open_card(0)
        await page.locator('#transcript-regenerate').click()
        await dialog.get_by_role('button', name='重新生成', exact=True).click()
        await expect(page.locator('#transcript-editor')).to_have_value('作品1新字幕')
        assert extraction_calls == [ids[0], ids[0], ids[0]]
        assert extraction_options == [False, False, True]
        await tabs.get_by_role('tab', name='AI 总结', exact=True).click()
        await expect(page.locator('#summary-markdown')).to_contain_text('作品1模拟总结')
        await expect(progressive.locator('.card-summary-completed')).to_have_text('AI总结')
        assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert errors == []
        await page.screenshot(path=str(tmp_path/f'card-actions-{width}.png'), full_page=True)
        await browser.close()
