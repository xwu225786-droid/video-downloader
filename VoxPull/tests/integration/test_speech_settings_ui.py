import json

import pytest
from playwright.async_api import async_playwright, expect
from test_card_actions_ui import static_app  # noqa: F401


@pytest.mark.parametrize('width', [1280, 390])
async def test_speech_configuration_ui(static_app, width):  # noqa: F811
    saved = {'provider': 'local', 'base_url': 'https://api.siliconflow.cn/v1',
             'model': 'FunAudioLLM/SenseVoiceSmall', 'has_api_key': False, 'cloud': False}
    requests = []
    llm_writes = []
    llm_config = {"configured": False, "model": "", "base_url": ""}
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
                if route.request.method == 'PUT':
                    data = route.request.post_data_json
                    llm_writes.append(data)
                    llm_config.update(configured=True, model=data['model'], base_url=data['base_url'])
                data = llm_config
            elif path == 'summary/models':
                data = {'models': ['llm-test-model']}
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
        assert await page.locator('.ai-model-settings #speech-settings').count() == 1
        assert await page.locator('.ai-model-settings #llm-settings').count() == 1
        await expect(page.locator('#speech-settings summary')).to_contain_text('语音模型')
        await expect(page.locator('#llm-settings summary')).to_contain_text('LLM 处理模型')
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
        assert llm_writes == []
        await page.locator('#llm-settings summary').click()
        await page.locator('#summary-config-open').click()
        await page.locator('#summary-config-base').fill('https://llm.example/v1')
        await page.locator('#summary-config-key').fill('fake-llm-key')
        await page.locator('#summary-config-key').press('Tab')
        await expect(page.locator('#summary-config-model-trigger')).to_be_enabled()
        await page.locator('#summary-config-model-trigger').click()
        await page.locator('#summary-config-model-list .summary-model-option').filter(has_text='llm-test-model').click()
        await page.locator('#summary-config-save').click()
        await expect(page.locator('#summary-config-dialog')).not_to_be_visible()
        assert len(llm_writes) == 1 and llm_writes[0]['api_key'] == 'fake-llm-key'
        assert len(requests) == 1, 'LLM save must not update speech configuration'
        await expect(page.locator('#speech-model')).to_have_value('FunAudioLLM/SenseVoiceSmall')
        await page.reload()
        await page.locator('#settings-open').click()
        await page.locator('#speech-settings summary').click()
        await expect(page.locator('#speech-provider')).to_have_value('siliconflow')
        await expect(page.locator('#speech-key')).to_have_value('')
        assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert await page.locator('#speech-base').evaluate('(e) => e.getBoundingClientRect().width > 200')
        await page.locator('.ai-model-settings').screenshot(path=f'/tmp/voxpull-ai-settings-{width}.png')
        page.once('dialog', lambda dialog: dialog.accept())
        await page.locator('#speech-clear').click()
        await expect(page.locator('#speech-provider')).to_have_value('local')
        assert llm_config['configured'] and llm_config['model'] == 'llm-test-model'
        assert errors == []
        await browser.close()
