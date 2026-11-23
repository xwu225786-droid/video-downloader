from unittest.mock import AsyncMock

import httpx

from voxpull.app import create_app
from voxpull.domain.models import ComponentStatus, SystemSnapshot
from test_api import make_settings


async def test_config_round_trip_without_exposing_key_and_cloud_health(tmp_path):
    app = create_app(make_settings(tmp_path))
    async with app.router.lifespan_context(app):
        c = app.state.container
        yes, no = ComponentStatus(True, 'ready'), ComponentStatus(False, 'missing')
        c.system_service.status = AsyncMock(return_value=SystemSnapshot(yes, yes, yes, yes, yes, yes, no, no, no))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            assert (await client.get('/api/transcription/config')).json()['provider'] == 'local'
            payload = {'provider': 'siliconflow', 'base_url': 'https://api.siliconflow.cn/v1',
                       'model': 'FunAudioLLM/SenseVoiceSmall', 'api_key': 'test-only-secret'}
            response = await client.put('/api/transcription/config', json=payload)
            assert response.status_code == 200 and 'test-only-secret' not in response.text
            assert response.json()['has_api_key']
            assert c.job_service.pipeline.transcriber is c.transcription_provider
            status = (await client.get('/api/system')).json()
            assert status['ready'] and status['transcription_cloud'] and not status['model']['ready']
            assert (await client.delete('/api/transcription/config')).status_code == 204
            assert not (await client.get('/api/system')).json()['ready']


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
