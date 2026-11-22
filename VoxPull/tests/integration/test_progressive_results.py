import asyncio
from pathlib import Path

import httpx
import pytest

from test_api import FakeSummaryProvider, install_fake_summary_provider, make_settings
from test_pipeline import FakeAudioExtractor, FakeBrowser, FakeCoverExtractor, FakeDownloader, FakeTranscriber
from voxpull.app import create_app
from voxpull.domain.errors import SummaryProviderFailedError, TranscriptionFailedError
from voxpull.domain.models import Job, JobBatch, JobStage, JobStatus, Transcript, VideoSummary


def progressive_app(tmp_path, provider, save_video=True):
    app = create_app(make_settings(tmp_path))
    service = app.state.container.job_service
    pipeline = service.pipeline
    pipeline.browser = FakeBrowser()
    pipeline.downloader = FakeDownloader()
    pipeline.audio_extractor = FakeAudioExtractor()
    pipeline.cover_extractor = FakeCoverExtractor()
    pipeline.transcriber = FakeTranscriber()
    provider.configured = True
    provider.model = 'mock-model'
    install_fake_summary_provider(app, provider)
    pipeline.summary_service = app.state.container.summary_service
    ident = 'd'*32
    service.repository.add(Job(ident, 'https://www.douyin.com/video/123', 'zh', save_video=save_video,
                               metadata={'auto_summary': True}))
    service._batches['test-batch'] = JobBatch('test-batch', (ident,), 'zh', True)
    return app, pipeline, ident


@pytest.mark.parametrize('save_video', [True, False])
async def test_downloaded_video_is_available_before_cover_subtitles_and_summary_finish(tmp_path, save_video):
    cover_started, allow_cover = asyncio.Event(), asyncio.Event()
    speech_started, allow_speech = asyncio.Event(), asyncio.Event()
    summary_started, allow_summary = asyncio.Event(), asyncio.Event()
    class Provider(FakeSummaryProvider):
        async def summarize(self, text, style):
            assert text == '阶段字幕'
            summary_started.set()
            await allow_summary.wait()
            return VideoSummary(markdown='阶段总结')
    app, pipeline, ident = progressive_app(tmp_path, Provider(), save_video)
    class Cover:
        async def extract(self, video, target):
            cover_started.set()
            await allow_cover.wait()
            await FakeCoverExtractor().extract(video, target)
    class Speech:
        async def transcribe(self, *args):
            speech_started.set()
            await allow_speech.wait()
            return Transcript('阶段字幕', (), 'zh')
    pipeline.cover_extractor, pipeline.transcriber = Cover(), Speech()
    task = asyncio.create_task(pipeline.execute(ident))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
            await asyncio.wait_for(cover_started.wait(), 2)
            early = (await client.get(f'/api/jobs/{ident}')).json()
            assert early['status'] == 'running' and early['result']['transcript'] is None
            assert early['result']['media']['video_url'] == f'/api/jobs/{ident}/video'
            assert early['result']['media']['cover_path'] is None
            assert early['result']['media']['saved'] is save_video
            assert early['subtitle_state'] == 'generating' and early['summary_state'] == 'waiting'
            assert (await client.get(f'/api/jobs/{ident}/video')).content == b'fake mp4'
            batch = (await client.get('/api/batches/test-batch')).json()
            assert batch['jobs'][0]['result_available'] and batch['jobs'][0]['status'] == 'running'
            assert batch['jobs'][0]['summary_state'] == 'waiting'
            allow_cover.set()
            await asyncio.wait_for(speech_started.wait(), 2)
            assert not task.done()
            allow_speech.set()
            await asyncio.wait_for(summary_started.wait(), 2)
            during = (await client.get(f'/api/jobs/{ident}')).json()
            assert during['status'] == 'running'
            assert during['subtitle_state'] == 'completed' and during['summary_state'] == 'generating'
            assert during['result']['transcript']['text'] == '阶段字幕'
            allow_summary.set()
            await asyncio.wait_for(asyncio.shield(task), 2)
            done = (await client.get(f'/api/jobs/{ident}')).json()
            assert done['status'] == 'completed' and done['summary_state'] == 'completed'
            assert done['summary']['markdown'] == '阶段总结'
            assert Path(done['result']['media']['absolute_path']).is_file() is save_video
            assert (await client.get(f'/api/jobs/{ident}/video')).status_code == (200 if save_video else 404)
    finally:
        allow_cover.set()
        allow_speech.set()
        allow_summary.set()
        await task


@pytest.mark.parametrize('failure', ['speech', 'summary'])
async def test_later_processing_failure_keeps_downloaded_video_available(tmp_path, failure):
    class Provider(FakeSummaryProvider):
        async def summarize(self, *args):
            raise SummaryProviderFailedError()
    app, pipeline, ident = progressive_app(tmp_path, Provider())
    if failure == 'speech':
        class Speech:
            async def transcribe(self, *args):
                raise TranscriptionFailedError()
        pipeline.transcriber = Speech()
    await pipeline.execute(ident)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
        job = (await client.get(f'/api/jobs/{ident}')).json()
        assert Path(job['result']['media']['absolute_path']).is_file()
        assert (await client.get(f'/api/jobs/{ident}/video')).status_code == 200
        if failure == 'speech':
            assert job['status'] == 'failed' and job['subtitle_state'] == 'failed'
        else:
            assert job['status'] == 'completed' and job['summary_state'] == 'failed'
            assert job['result']['transcript']['text'] == '你好'


async def test_single_batch_and_retry_preserve_explicit_auto_summary_choice(tmp_path):
    app = create_app(make_settings(tmp_path))
    service = app.state.container.job_service
    service._accepting = True
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
            single = await client.post('/api/jobs', json={'content':'https://example.test/1', 'auto_summary':True})
            assert single.status_code == 202
            assert service.get(single.json()['job_id']).metadata['auto_summary'] is True
            batch = await client.post('/api/batches', json={'content':'https://example.test/2', 'auto_summary':True})
            assert batch.status_code == 202
            ident = batch.json()['jobs'][0]['id']
            assert service.get(ident).metadata['auto_summary'] is True
            service.repository.update(ident, status=JobStatus.FAILED, stage=JobStage.FAILED)
            retried = service.retry_batch(batch.json()['id'])
            assert service.get(retried.job_ids[0]).metadata['auto_summary'] is True
    finally:
        await service.stop()
