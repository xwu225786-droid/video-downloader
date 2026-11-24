from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from voxpull.domain.errors import (
    SummaryConfigBusyError,
    SummaryInvalidInputError,
    SummaryNotAvailableError,
    SummaryUnavailableError,
)
from voxpull.domain.models import (
    JobStatus,
    MediaKind,
    SummaryProviderStatus,
    SummaryStyle,
    VideoSummary,
)
from voxpull.domain.ports import JobRepositoryPort, SummaryConfiguratorPort, SummarizerPort


class SummaryService:
    """Coordinates optional AI summaries without changing the original job state."""

    def __init__(
        self,
        repository: JobRepositoryPort,
        summarizer: SummarizerPort,
        configurator: SummaryConfiguratorPort,
        *,
        max_input_chars: int,
        max_concurrency: int,
    ) -> None:
        self._repository = repository
        self._summarizer = summarizer
        self._configurator = configurator
        self._max_input_chars = max(1, max_input_chars)
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self._activity_lock = asyncio.Lock()
        self._active_requests = 0

    def status(self) -> SummaryProviderStatus:
        return self._configurator.status()

    async def configure(self, base_url: str, api_key: str, model: str) -> None:
        async with self._activity_lock:
            if self._active_requests:
                raise SummaryConfigBusyError()
            await self._configurator.configure(base_url, api_key, model)

    async def clear_configuration(self) -> None:
        async with self._activity_lock:
            if self._active_requests:
                raise SummaryConfigBusyError()
            await self._configurator.clear()

    async def test_connection(self, base_url: str, api_key: str, model: str) -> dict:
        return await self._summarizer.test_connection(base_url, api_key, model)

    async def list_models(self, base_url: str, api_key: str) -> list[str]:
        return await self._summarizer.list_models(base_url, api_key)

    async def summarize(self, job_id: str, transcript_text: str, style: SummaryStyle) -> VideoSummary:
        job = self._repository.get(job_id)
        if job is None:
            raise SummaryNotAvailableError("任务不存在")
        if (
            job.status not in {JobStatus.COMPLETED, JobStatus.RUNNING}
            or job.result is None
            or not ((job.result.media.kind is MediaKind.VIDEO and job.result.transcript is not None)
                    or (job.result.media.kind is MediaKind.IMAGES and job.result.media.description.strip()))
        ):
            raise SummaryNotAvailableError()

        text = transcript_text.strip()
        if not text:
            raise SummaryInvalidInputError("总结文案不能为空")
        if len(text) > self._max_input_chars:
            raise SummaryInvalidInputError(
                f"总结文案超过最大长度（{self._max_input_chars} 个字符）"
            )

        async with self._activity_lock:
            if not self._configurator.status().configured:
                raise SummaryUnavailableError()
            self._active_requests += 1

        try:
            self._save_state(job_id, "generating")
            async with self._semaphore:
                summary = await self._summarizer.summarize(
                    text,
                    style,
                )
                current = self._repository.get(job_id)
                if current is not None:
                    self._repository.update(job_id, metadata={**current.metadata, "summary_state": "completed", "ai_summary": {
                        "markdown": summary.markdown, "source_text": transcript_text,
                        "model": self.status().model, "style": style.value,
                        "generated_at": datetime.now(UTC).isoformat(),
                    }})
                return summary
        except BaseException:
            self._save_state(job_id, "failed")
            raise
        finally:
            async with self._activity_lock:
                self._active_requests -= 1

    def _save_state(self, job_id: str, state: str) -> None:
        job = self._repository.get(job_id)
        if job is not None:
            self._repository.update(job_id, metadata={**job.metadata, "summary_state": state})
