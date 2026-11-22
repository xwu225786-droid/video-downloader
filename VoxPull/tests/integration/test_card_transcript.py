import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import httpx

from test_api import FakeSummaryProvider, install_fake_summary_provider, make_settings
from voxpull.app import create_app
from voxpull.domain.errors import TranscriptionFailedError
from voxpull.domain.models import Job, JobResult, JobStage, JobStatus, MediaInfo, MediaKind, Transcript
from voxpull.infrastructure.job_records import FileJobRepository


def setup_job(tmp_path):
    app = create_app(make_settings(tmp_path))
    service = app.state.container.job_service
    folder = tmp_path/'作品'
    folder.mkdir()
    video = folder/'视频.mp4'
    video.write_bytes(b'original video')
    (folder/'文案.txt').write_text('用户手稿')
    ident = 'a'*32
    service.repository.add(Job(ident, 'https://example.test', 'zh',
        status=JobStatus.COMPLETED, stage=JobStage.COMPLETED, extract_txt=False,
        metadata={'tag': '保留标签', 'source_files': [str(video)]},
        result=JobResult(MediaInfo('123', '作品', MediaKind.VIDEO, video.name, str(video), True))))
    async def extract(source, target):
        assert source == video
        target.write_bytes(b'wav')
    service.pipeline.audio_extractor.extract = AsyncMock(side_effect=extract)
    return app, service, ident, video


async def test_existing_card_gets_subtitles_without_redownload_or_overwriting_files(tmp_path):
    app, service, ident, video = setup_job(tmp_path)
    async def transcribe(*args):
        await asyncio.sleep(.01)
        return Transcript('新字幕', (), 'zh')
    service.pipeline.transcriber.transcribe = AsyncMock(side_effect=transcribe)
    service.pipeline.downloader.download = AsyncMock(side_effect=AssertionError('不可重新下载'))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
        results = await asyncio.gather(*[client.post(f'/api/jobs/{ident}/transcript') for _ in range(2)])
    assert all(response.status_code == 200 for response in results)
    assert results[0].json()['result']['transcript']['text'] == '新字幕'
    service.pipeline.transcriber.transcribe.assert_awaited_once()
    assert video.read_bytes() == b'original video'
    assert (video.parent/'文案.txt').read_text() == '用户手稿'
    assert (video.parent/'字幕文案.txt').read_text() == '新字幕'
    updated = service.get(ident)
    assert updated.status == JobStatus.COMPLETED and updated.metadata['tag'] == '保留标签'
    assert updated.result.media.absolute_path == str(video)
    assert str(video.parent/'字幕文案.txt') in updated.metadata['source_files']


async def test_failed_extraction_keeps_completed_result_and_reports_clear_errors(tmp_path):
    app, service, ident, video = setup_job(tmp_path)
    service.pipeline.transcriber.transcribe = AsyncMock(side_effect=TranscriptionFailedError())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
        assert (await client.post(f'/api/jobs/{ident}/transcript', headers={'Origin':'https://outside.test'})).status_code == 403
        assert (await client.post(f'/api/jobs/{ident}/transcript')).status_code == 502
        failed = (await client.get(f'/api/jobs/{ident}/transcript/status')).json()
        assert failed['state'] == 'failed' and failed['message'] == '语音识别失败'
        assert (await client.post('/api/jobs/missing/transcript')).status_code == 404
        video.unlink()
        assert (await client.post(f'/api/jobs/{ident}/transcript')).status_code == 422
    assert service.get(ident).status == JobStatus.COMPLETED
    assert service.get(ident).result.transcript is None
    assert (video.parent/'文案.txt').read_text() == '用户手稿'
    assert not list(service.pipeline.storage.work_root.glob('subtitle-*'))


async def test_card_reports_real_progress_without_changing_completed_job(tmp_path):
    app, service, ident, video = setup_job(tmp_path)
    started, finish = asyncio.Event(), asyncio.Event()
    async def transcribe(audio, language, work, progress):
        progress(37, '正在识别语音')
        started.set()
        await finish.wait()
        return Transcript('完成字幕', (), 'zh')
    service.pipeline.transcriber.transcribe = AsyncMock(side_effect=transcribe)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
        assert (await client.get(f'/api/jobs/{ident}/transcript/status')).json()['state'] == 'idle'
        request = asyncio.create_task(client.post(f'/api/jobs/{ident}/transcript'))
        try:
            await asyncio.wait_for(started.wait(), 2)
            response = await client.get(f'/api/jobs/{ident}/transcript/status')
            state = response.json()
            assert state['state'] == 'running' and state['progress'] == 37
            assert state['message'] == '正在识别语音' and state['elapsed_seconds'] >= 0
            assert service.get(ident).status == JobStatus.COMPLETED
            assert service.get(ident).result.transcript is None
        finally:
            finish.set()
            response = await request
        assert response.status_code == 200
        assert (await client.get(f'/api/jobs/{ident}/transcript/status')).json()['state'] == 'completed'
        assert (await client.get('/api/jobs/missing/transcript/status')).status_code == 404


async def test_confirmed_regeneration_runs_again_and_keeps_previous_subtitle_on_failure(tmp_path):
    app, service, ident, video = setup_job(tmp_path)
    service.pipeline.transcriber.transcribe = AsyncMock(return_value=Transcript('初次字幕', (), 'zh'))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
        first = (await client.post(f'/api/jobs/{ident}/transcript')).json()
        first_path = first['result']['media']['description_path']
        assert (await client.post(f'/api/jobs/{ident}/transcript')).status_code == 200
        service.pipeline.transcriber.transcribe.assert_awaited_once()
        started, finish = asyncio.Event(), asyncio.Event()
        async def transcribe(*args):
            args[-1](46, '正在识别语音')
            started.set()
            await finish.wait()
            return Transcript('重新生成字幕', (), 'zh')
        service.pipeline.transcriber.transcribe = AsyncMock(side_effect=transcribe)
        request = asyncio.create_task(client.post(f'/api/jobs/{ident}/transcript?regenerate=true'))
        try:
            await asyncio.wait_for(started.wait(), 2)
            state = (await client.get(f'/api/jobs/{ident}/transcript/status')).json()
            assert state['state'] == 'running' and state['progress'] == 46
            assert service.get(ident).result.transcript.text == '初次字幕'
        finally:
            finish.set()
            second = (await request).json()
        assert second['result']['transcript']['text'] == '重新生成字幕'
        assert second['result']['media']['description_path'] != first_path
        assert Path(first_path).read_text() == '初次字幕'
        previous = service.get(ident).result
        service.pipeline.transcriber.transcribe = AsyncMock(side_effect=TranscriptionFailedError())
        assert (await client.post(f'/api/jobs/{ident}/transcript?regenerate=true')).status_code == 502
        assert service.get(ident).result == previous
        assert service.get(ident).status == JobStatus.COMPLETED


async def test_completed_summary_and_badges_survive_record_reload(tmp_path):
    app, service, ident, video = setup_job(tmp_path)
    service.pipeline.transcriber.transcribe = AsyncMock(return_value=Transcript('原字幕', (), 'zh'))
    provider = FakeSummaryProvider()
    provider.configured = True
    provider.model = 'mock-model'
    install_fake_summary_provider(app, provider)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
        await client.post(f'/api/jobs/{ident}/transcript')
        response = await client.post(f'/api/jobs/{ident}/summary', json={'transcript_text':'编辑后的文案'})
        assert response.status_code == 200
    reloaded = FileJobRepository(service.repository.root)
    reloaded.load()
    app.state.container.job_service.repository = reloaded
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
        detail = (await client.get(f'/api/jobs/{ident}')).json()
    assert detail['summary']['markdown'] == response.json()['markdown']
    assert detail['summary']['source_text'] == '编辑后的文案'
    assert detail['summary']['model'] == 'mock-model'
    assert detail['result']['transcript']['text'] == '原字幕'
    assert reloaded.get(ident).metadata['tag'] == '保留标签'
