from unittest.mock import AsyncMock

import httpx

from voxpull.app import create_app
from voxpull.domain.models import ComponentStatus, SystemSnapshot
from test_api import make_settings


async def test_config_round_trip_without_exposing_key_and_cloud_health(tmp_path):
    app = create_app(make_settings(tmp_path))
    async with app.router.lifespan_context(app):
        c = app.state.container
        yes = ComponentStatus(True, 'ready')
        c.system_service.status = AsyncMock(return_value=SystemSnapshot(yes, yes, yes, yes, yes, yes))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            assert (await client.get('/api/transcription/config')).json()['configured'] is False
            payload = {'provider': 'siliconflow', 'base_url': 'https://api.siliconflow.cn/v1',
                       'model': 'FunAudioLLM/SenseVoiceSmall', 'api_key': 'test-only-secret'}
            response = await client.put('/api/transcription/config', json=payload)
            assert response.status_code == 200 and 'test-only-secret' not in response.text
            assert response.json()['has_api_key']
            assert c.job_service.pipeline.transcriber is c.transcription_provider
            status = (await client.get('/api/system')).json()
            assert status['ready'] and 'whisper_cpp' not in status
            assert (await client.delete('/api/transcription/config')).status_code == 204
            assert (await client.get('/api/system')).json()['ready']
            assert not (await client.get('/api/transcription/config')).json()['configured']


async def test_saved_card_cloud_transcription_then_summary_and_failed_regeneration(tmp_path):
    import wave
    from pathlib import Path
    from test_card_transcript import setup_job
    from test_api import FakeSummaryProvider, install_fake_summary_provider
    app, service, ident, video = setup_job(tmp_path)
    cloud = app.state.container.transcription_provider
    cloud.transport = httpx.MockTransport(lambda _: httpx.Response(200, json={'text': '雲端字幕內容'}))
    async def extract(source, target):
        with wave.open(str(target), 'wb') as wav:
            wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            wav.writeframes(b'\0\0' * 16000)
    service.pipeline.audio_extractor.extract = AsyncMock(side_effect=extract)
    service.pipeline.downloader.download = AsyncMock(side_effect=AssertionError('must reuse saved video'))
    summary = FakeSummaryProvider()
    summary.configured = True
    summary.model = 'test-model'
    install_fake_summary_provider(app, summary)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        await client.put('/api/transcription/config', json={'provider': 'siliconflow',
            'api_key': 'test-key', 'model': 'FunAudioLLM/SenseVoiceSmall'})
        response = await client.post(f'/api/jobs/{ident}/transcript')
        assert response.status_code == 200
        result = response.json()['result']
        assert result['transcript']['text'] == '云端字幕内容' and not result['transcript']['segments']
        assert Path(result['media']['description_path']).read_text(encoding='utf-8') == '云端字幕内容'
        assert video.read_bytes() == b'original video'
        response = await client.post(f'/api/jobs/{ident}/summary', json={'style': 'brief', 'transcript_text': '云端字幕内容'})
        assert response.status_code == 200, response.text
        cloud.transport = httpx.MockTransport(lambda _: httpx.Response(401, text='private credential error'))
        response = await client.post(f'/api/jobs/{ident}/transcript?regenerate=true')
        assert response.status_code == 502 and 'API Key' in response.text
        assert service.get(ident).result.transcript.text == '云端字幕内容'
        assert service.get(ident).status.value == 'completed'


async def test_model_probe_api_is_independent_of_saved_configuration(tmp_path):
    app = create_app(make_settings(tmp_path))
    async with app.router.lifespan_context(app):
        provider = app.state.container.transcription_provider
        provider.transport = httpx.MockTransport(lambda request: httpx.Response(200,
            json={'data': [{'id': 'whisper-test'}]} if request.url.path.endswith('/models') else {'text': 'Hello test'}))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            original = (await client.get('/api/transcription/config')).json()
            config = {'provider':'compatible', 'base_url':'https://asr.example/v1', 'model':'whisper-test', 'api_key':'test-key'}
            response = await client.post('/api/transcription/test', json=config)
            assert response.status_code == 200 and response.json()['ok']
            assert 'test-key' not in response.text
            assert (await client.post('/api/transcription/models', json=config)).json()['models'] == ['whisper-test']
            assert (await client.get('/api/transcription/config')).json() == original


async def test_llm_connection_probe_api_without_saving(tmp_path):
    from types import SimpleNamespace
    app = create_app(make_settings(tmp_path))
    async with app.router.lifespan_context(app):
        provider = app.state.container.summary_provider
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='OK'))])
        probe = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=response))), close=AsyncMock())
        provider._client_factory = lambda *_: probe
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            before = (await client.get('/api/summary/config')).json()
            speech_before = (await client.get('/api/transcription/config')).json()
            response = await client.post('/api/summary/test',json={'base_url':'https://probe.example/v1', 'api_key':'test-key', 'model':'test-model'})
            assert response.status_code == 200 and response.json()['ok'] and response.json()['text'] == 'OK'
            assert (await client.get('/api/summary/config')).json() == before
            assert (await client.get('/api/transcription/config')).json() == speech_before
