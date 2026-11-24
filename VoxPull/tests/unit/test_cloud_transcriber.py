import json
import asyncio
import io
import wave

import httpx
import pytest

from voxpull.domain.errors import DependencyMissingError, InvalidInputError, TranscriptionFailedError
from voxpull.infrastructure.cloud_transcriber import CloudTranscriber, SILICONFLOW_BASE, SILICONFLOW_MODEL


def audio_file(tmp_path, seconds=1):
    path = tmp_path / '中文 音频.wav'
    with wave.open(str(path), 'wb') as output:
        output.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        output.writeframes(b'\0\0' * int(seconds * 16000))
    return path


def provider(tmp_path, handler=None):
    return CloudTranscriber(tmp_path / 'auth/speech.json',
        transport=httpx.MockTransport(handler) if handler else None)


async def test_unconfigured_default_and_persist_cloud_selection(tmp_path):
    service = provider(tmp_path)
    with pytest.raises(DependencyMissingError, match='云端接口配置'):
        await service.transcribe(None, 'zh', tmp_path, lambda *_: None)
    service.configure('siliconflow', SILICONFLOW_BASE, SILICONFLOW_MODEL, 'test-secret')
    assert 'test-secret' not in str(service.status())
    assert 'test-secret' not in repr(service.config)
    restored = provider(tmp_path)
    restored.load()
    assert restored.config.api_key == 'test-secret'
    with pytest.raises(InvalidInputError, match='不支持'):
        restored.configure('local', SILICONFLOW_BASE, SILICONFLOW_MODEL, '')
    restored.configure('siliconflow', SILICONFLOW_BASE, SILICONFLOW_MODEL, '')
    assert restored.config.api_key == 'test-secret'
    with pytest.raises(InvalidInputError, match='Key'):
        restored.configure('compatible', 'https://other.example/v1', 'asr', '')
    assert restored.config.provider == 'siliconflow'
    restored.clear()
    assert not restored.config_path.exists() and not restored.status()['configured']


async def test_siliconflow_multipart_and_text_without_invented_timestamps(tmp_path):
    def handler(request):
        assert str(request.url) == SILICONFLOW_BASE + '/audio/transcriptions'
        assert request.headers['authorization'] == 'Bearer test-key'
        body = request.read()
        assert b'filename="audio.wav"' in body and SILICONFLOW_MODEL.encode() in body
        assert b'name="language"' not in body and b'RIFF' in body
        return httpx.Response(200, json={'text': '這是識別結果'})
    service = provider(tmp_path, handler)
    service.configure('siliconflow', SILICONFLOW_BASE + '/audio/transcriptions', SILICONFLOW_MODEL, 'test-key')
    result = await service.transcribe(audio_file(tmp_path), 'zh', tmp_path, lambda *_: None)
    assert result.text == '这是识别结果' and result.segments == ()
    assert result.detected_language == 'unknown'


async def test_long_audio_chunks_order_and_real_segment_offsets(tmp_path, monkeypatch):
    from voxpull.infrastructure import cloud_transcriber
    monkeypatch.setattr(cloud_transcriber, 'CHUNK_SECONDS', 1)
    calls = []
    def handler(request):
        body = request.read()
        assert b'name="language"' in body
        # The multipart upload must contain an independently decodable WAV.
        start = body.index(b'RIFF')
        with wave.open(io.BytesIO(body[start:]), 'rb') as wav:
            assert 0 < wav.getnframes() <= 16000
        calls.append(request)
        return httpx.Response(200, json={'text': f'片段{len(calls)}', 'language': 'zh',
            'segments': [{'start': .1, 'end': .4, 'text': '真實時間'},
                         {'start': -1, 'end': 1000, 'text': 'invalid'}]})
    service = provider(tmp_path, handler)
    service.configure('compatible', 'https://asr.example/v1', 'asr-model', 'key')
    progress = []
    result = await service.transcribe(audio_file(tmp_path, 2.5), 'zh', tmp_path, lambda p, _: progress.append(p))
    assert result.text == '片段1\n片段2\n片段3' and len(calls) == 3
    assert [s.start_ms for s in result.segments] == [100, 1100, 2100]
    assert progress[-1] == 100


@pytest.mark.parametrize('status', [401, 403, 404, 413, 429, 503, 302])
async def test_cloud_errors_do_not_leak_keys_or_fallback(tmp_path, status):
    service = provider(tmp_path, lambda _: httpx.Response(status, text='secret-key and private provider details'))
    service.configure('siliconflow', SILICONFLOW_BASE, SILICONFLOW_MODEL, 'secret-key')
    with pytest.raises(TranscriptionFailedError) as error:
        await service.transcribe(audio_file(tmp_path), 'auto', tmp_path, lambda *_: None)
    assert 'secret-key' not in str(error.value) and 'private' not in str(error.value)
    assert service._active == 0


@pytest.mark.parametrize('payload', [{}, {'text': None}, {'text': ''}, [], 'invalid'])
async def test_invalid_cloud_responses(tmp_path, payload):
    service = provider(tmp_path, lambda _: httpx.Response(200, json=payload))
    service.configure('compatible', 'https://asr.example/v1', 'asr', 'key')
    with pytest.raises(TranscriptionFailedError):
        await service.transcribe(audio_file(tmp_path), 'auto', tmp_path, lambda *_: None)


async def test_timeout_and_cancellation_release_busy_state(tmp_path):
    started = asyncio.Event()
    async def handler(request):
        started.set()
        await asyncio.sleep(60)
    service = provider(tmp_path, handler)
    service.configure('compatible', 'https://asr.example/v1', 'asr', 'key')
    task = asyncio.create_task(service.transcribe(audio_file(tmp_path), 'auto', tmp_path, lambda *_: None))
    await asyncio.wait_for(started.wait(), 3)
    with pytest.raises(InvalidInputError, match='正在进行'):
        service.clear()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert service._active == 0
    def timeout(request):
        raise httpx.ReadTimeout('key', request=request)
    service.transport = httpx.MockTransport(timeout)
    with pytest.raises(TranscriptionFailedError, match='超时'):
        await service.transcribe(audio_file(tmp_path), 'auto', tmp_path, lambda *_: None)


@pytest.mark.parametrize('url', ['https://user:password@asr.example/v1', 'file:///tmp/secret', 'https://[', 'https://asr.example/v1?q=key'])
def test_bad_endpoint_not_saved(tmp_path, url):
    service = provider(tmp_path)
    with pytest.raises(InvalidInputError):
        service.configure('compatible', url, 'asr', 'key')
    assert not service.config_path.exists()


async def test_probe_uses_unsaved_values_real_sample_and_does_not_save(tmp_path):
    seen = []
    def handler(request):
        assert str(request.url) == 'https://test-asr.example/v1/audio/transcriptions'
        assert request.headers['authorization'] == 'Bearer probe-key'
        body = request.read()
        assert b'RIFF' in body and b'speech-test.wav' in body and b'probe-model' in body
        seen.append(request)
        return httpx.Response(200, json={'text': 'Hello, this is a test.'})
    service = provider(tmp_path, handler)
    before = service.status()
    result = await service.test_connection(provider='compatible', base_url='https://test-asr.example/v1', model='probe-model', api_key='probe-key')
    assert result['ok'] and result['text'] and result['elapsed_ms'] >= 0
    assert service.status() == before and not service.config_path.exists() and len(seen) == 1


@pytest.mark.parametrize('status', [401, 403, 404, 429, 503, 302])
async def test_probe_reports_api_failures_without_saving_or_leaking_key(tmp_path, status):
    service = provider(tmp_path, lambda _: httpx.Response(status, text='private probe-key'))
    with pytest.raises(TranscriptionFailedError) as error:
        await service.test_connection(provider='compatible', base_url='https://asr.example/v1', model='asr', api_key='probe-key')
    assert 'probe-key' not in str(error.value) and not service.config_path.exists()


async def test_probe_saved_key_only_for_same_endpoint_and_models_are_filtered(tmp_path):
    def handler(request):
        assert request.headers['authorization'] == 'Bearer saved-key'
        if request.url.path.endswith('/models'):
            return httpx.Response(200, json={'data': [{'id': 'chat-model'}, {'id': 'FunAudioLLM/SenseVoiceSmall'}]})
        return httpx.Response(200, json={'text': 'hello'})
    service = provider(tmp_path, handler)
    service.configure('siliconflow', SILICONFLOW_BASE, SILICONFLOW_MODEL, 'saved-key')
    original = service.config_path.read_bytes()
    payload = dict(provider='siliconflow', base_url=SILICONFLOW_BASE, model=SILICONFLOW_MODEL, api_key='')
    assert await service.list_models(**payload) == [SILICONFLOW_MODEL]
    assert (await service.test_connection(**payload))['ok']
    assert service.config_path.read_bytes() == original
    with pytest.raises(InvalidInputError):
        await service.test_connection(**{**payload, 'base_url': 'https://another.example/v1'})


@pytest.mark.parametrize('payload', [{}, {'text': ''}, {'text': None}, 'not an object'])
async def test_probe_does_not_claim_success_without_recognized_text(tmp_path, payload):
    service = provider(tmp_path, lambda _: httpx.Response(200, json=payload))
    with pytest.raises(TranscriptionFailedError, match='未返回'):
        await service.test_connection(provider='siliconflow', base_url=SILICONFLOW_BASE, model=SILICONFLOW_MODEL, api_key='key')


async def test_legacy_offline_configuration_does_not_enable_cloud_upload(tmp_path):
    service = provider(tmp_path, lambda request: pytest.fail("Cloud call was not authorized"))
    service.config_path.parent.mkdir()
    service.config_path.write_text(json.dumps({
        'provider': 'local', 'base_url': SILICONFLOW_BASE,
        'model': SILICONFLOW_MODEL, 'api_key': 'previous-key',
    }), encoding='utf-8')
    service.load()
    assert not service.status()['configured']
    with pytest.raises(DependencyMissingError, match='云端接口配置'):
        await service.transcribe(audio_file(tmp_path), 'zh', tmp_path, lambda *_: None)
