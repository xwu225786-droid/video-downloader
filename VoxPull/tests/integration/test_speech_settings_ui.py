import json

import pytest
from playwright.async_api import async_playwright, expect
from test_card_actions_ui import static_app  # noqa: F401


@pytest.mark.parametrize('width', [1280, 390])
async def test_speech_configuration_ui(static_app, width):  # noqa: F811
    saved = {'provider': 'local', 'base_url': 'https://api.siliconflow.cn/v1',
             'model': 'FunAudioLLM/SenseVoiceSmall', 'has_api_key': False, 'cloud': False}
    requests = []
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': width, 'height': 1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        async def route_api(route):
            path = route.request.url.split('/api/', 1)[1]
            if path == 'transcription/config':
                if route.request.method == 'PUT':
                    data = route.request.post_data_json
                    requests.append(data)
                    saved.update({key: data[key] for key in ('provider', 'base_url', 'model')})
                    saved.update(has_api_key=True, cloud=data['provider'] != 'local')
                elif route.request.method == 'DELETE':
                    saved.update(provider='local', has_api_key=False, cloud=False)
                if route.request.method == 'DELETE':
                    return await route.fulfill(status=204)
                data = saved
            elif path == 'system':
                data = {key: {'ready': True, 'detail': 'ready'} for key in ('python', 'playwright', 'chromium', 'cookie', 'yt_dlp', 'ffmpeg', 'model', 'vad_model', 'whisper_cpp')}
                data.update(video_storage_path='/videos', image_storage_path='/images', transcription_cloud=saved['cloud'])
            elif path == 'auth/douyin/status':
                data = {'status': 'ready'}
            elif path == 'summary/config':
                data = {'configured': False, 'model': '', 'base_url': ''}
            elif path == 'material-tags':
                data = {'tags': [], 'assignments': {}}
            elif path.startswith('jobs'):
                data = {'jobs': []}
            else:
                data = {}
            await route.fulfill(content_type='application/json', body=json.dumps(data))
        await page.route('**/api/**', route_api)
        await page.goto(static_app)
        await page.locator('#settings-open').click()
        await page.locator('#speech-settings summary').click()
        await expect(page.locator('#speech-cloud-fields')).to_be_hidden()
        await page.locator('#speech-provider').select_option('siliconflow')
        await expect(page.locator('#speech-cloud-fields')).to_be_visible()
        await expect(page.locator('#speech-model')).to_have_value('FunAudioLLM/SenseVoiceSmall')
        await page.locator('#speech-key').fill('fake-test-key')
        await page.locator('#speech-save').click()
        await expect(page.locator('#speech-feedback')).to_have_text('识别设置已保存。')
        await expect(page.locator('#speech-key')).to_have_value('')
        assert requests[0]['api_key'] == 'fake-test-key'
        await page.reload()
        await page.locator('#settings-open').click()
        await page.locator('#speech-settings summary').click()
        await expect(page.locator('#speech-provider')).to_have_value('siliconflow')
        await expect(page.locator('#speech-key')).to_have_value('')
        assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.once('dialog', lambda dialog: dialog.accept())
        await page.locator('#speech-clear').click()
        await expect(page.locator('#speech-provider')).to_have_value('local')
        assert errors == []
        await browser.close()
