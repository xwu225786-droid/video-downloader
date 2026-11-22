import asyncio
from dataclasses import replace

import pytest

from voxpull.application.job_service import InMemoryJobRepository
from voxpull.application.summary_service import SummaryService
from voxpull.domain.errors import (
    SummaryConfigBusyError,
    SummaryInvalidInputError,
    SummaryNotAvailableError,
    SummaryUnavailableError,
)
from voxpull.domain.models import (
    Job,
    JobResult,
    JobStage,
    JobStatus,
    MediaInfo,
    MediaKind,
    SummaryProviderStatus,
    SummaryStyle,
    Transcript,
    TranscriptSegment,
    VideoSummary,
)


class FakeSummaryProvider:
    def __init__(self) -> None:
        self.configured = False
        self.calls: list[tuple[str, SummaryStyle]] = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    def status(self) -> SummaryProviderStatus:
        return SummaryProviderStatus(
            configured=self.configured,
            base_url="https://example.test/v1",
            model="fake-model",
        )

    async def configure(self, base_url: str, api_key: str, model: str) -> None:
        self.configured = True

    async def clear(self) -> None:
        self.configured = False

    async def list_models(self, base_url: str, api_key: str) -> list[str]:
        return ["fake-model"]

    async def summarize(
        self,
        text: str,
        style: SummaryStyle,
    ) -> VideoSummary:
        self.calls.append((text, style))
        self.started.set()
        await self.release.wait()
        return VideoSummary(markdown="## 总结\n\n概要")


def completed_video_job(job_id: str = "video-job") -> Job:
    return Job(
        id=job_id,
        content="https://example.test/video",
        language="zh",
        status=JobStatus.COMPLETED,
        stage=JobStage.COMPLETED,
        progress=100,
        result=JobResult(
            media=MediaInfo(
                id="video",
                title="测试视频",
                kind=MediaKind.VIDEO,
                filename="video.mp4",
                absolute_path="/tmp/video.mp4",
                saved=True,
            ),
            transcript=Transcript(
                text="原始转写内容",
                segments=(TranscriptSegment(0, 1000, "原始第一段"),),
                detected_language="zh",
            ),
        ),
    )


async def test_summary_uses_current_editor_text_and_leaves_job_unchanged() -> None:
    repository = InMemoryJobRepository()
    repository.add(completed_video_job())
    provider = FakeSummaryProvider()
    provider.configured = True
    provider.release.set()
    service = SummaryService(
        repository,
        provider,
        provider,
        max_input_chars=20,
        max_concurrency=2,
    )

    await service.summarize("video-job", "编辑后的当前文案", SummaryStyle.DETAILED)

    assert provider.calls == [
        (
            "编辑后的当前文案",
            SummaryStyle.DETAILED,
        )
    ]
    stored = repository.get("video-job")
    assert stored is not None
    assert stored.result is not None
    assert stored.result.transcript is not None
    assert stored.result.transcript.text == "原始转写内容"


async def test_image_card_summarizes_current_body_without_a_video_transcript():
    repository = InMemoryJobRepository()
    job = completed_video_job('image-job')
    job.result = JobResult(replace(job.result.media, kind=MediaKind.IMAGES, description='图文原文'))
    repository.add(job)
    provider = FakeSummaryProvider()
    provider.configured = True
    provider.release.set()
    service = SummaryService(repository, provider, provider, max_input_chars=100, max_concurrency=1)
    await service.summarize('image-job', '编辑后的图文', SummaryStyle.BRIEF)
    assert provider.calls == [('编辑后的图文', SummaryStyle.BRIEF)]
    assert repository.get('image-job').result.media.description == '图文原文'


async def test_summary_rejects_unavailable_jobs_and_invalid_text() -> None:
    repository = InMemoryJobRepository()
    provider = FakeSummaryProvider()
    provider.configured = True
    service = SummaryService(
        repository,
        provider,
        provider,
        max_input_chars=4,
        max_concurrency=1,
    )

    with pytest.raises(SummaryNotAvailableError):
        await service.summarize("missing", "文本", SummaryStyle.BRIEF)

    repository.add(completed_video_job())
    with pytest.raises(SummaryInvalidInputError):
        await service.summarize("video-job", "  ", SummaryStyle.BRIEF)
    with pytest.raises(SummaryInvalidInputError):
        await service.summarize("video-job", "长度超过限制", SummaryStyle.BRIEF)

    provider.configured = False
    with pytest.raises(SummaryUnavailableError):
        await service.summarize("video-job", "正文", SummaryStyle.BRIEF)


async def test_summary_configuration_is_busy_while_a_request_is_running() -> None:
    repository = InMemoryJobRepository()
    repository.add(completed_video_job())
    provider = FakeSummaryProvider()
    provider.configured = True
    service = SummaryService(
        repository,
        provider,
        provider,
        max_input_chars=100,
        max_concurrency=1,
    )

    task = asyncio.create_task(service.summarize("video-job", "当前文案", SummaryStyle.BRIEF))
    await asyncio.wait_for(provider.started.wait(), timeout=1)
    with pytest.raises(SummaryConfigBusyError):
        await service.clear_configuration()
    provider.release.set()
    await task
    await service.clear_configuration()
    assert not provider.configured
