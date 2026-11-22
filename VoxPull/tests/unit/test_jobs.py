import asyncio

import pytest

from voxpull.application.job_service import InMemoryJobRepository, JobService
from voxpull.domain.models import Job, JobStage, JobStatus


def test_repository_returns_copies_and_validates_transitions() -> None:
    repository = InMemoryJobRepository()
    repository.add(Job(id="job-1", content="x", language="zh"))
    returned = repository.get("job-1")
    assert returned is not None
    returned.message = "changed outside"
    assert repository.get("job-1").message == "等待处理"

    repository.update("job-1", status=JobStatus.RUNNING, stage=JobStage.ACQUIRING_COOKIE)
    repository.update("job-1", stage=JobStage.DOWNLOADING)
    with pytest.raises(ValueError):
        repository.update("job-1", stage=JobStage.ACQUIRING_COOKIE)


async def test_job_service_runs_at_most_five_jobs_concurrently() -> None:
    class ControlledPipeline:
        def __init__(self) -> None:
            self.active = 0
            self.maximum_active = 0
            self.started = 0
            self.five_started = asyncio.Event()
            self.release = asyncio.Event()

        async def execute(self, _job_id: str) -> None:
            self.active += 1
            self.started += 1
            self.maximum_active = max(self.maximum_active, self.active)
            if self.active == 5:
                self.five_started.set()
            try:
                await self.release.wait()
            finally:
                self.active -= 1

    repository = InMemoryJobRepository()
    pipeline = ControlledPipeline()
    service = JobService(repository, pipeline, max_queue=10, max_concurrency=5)
    await service.start()
    try:
        for index in range(6):
            service.submit(f"https://example.com/{index}", "zh")

        await asyncio.wait_for(pipeline.five_started.wait(), timeout=1)
        await asyncio.sleep(0)
        assert service.has_active_jobs()
        assert pipeline.active == 5
        assert pipeline.started == 5

        pipeline.release.set()
        await asyncio.wait_for(service.queue.join(), timeout=1)
        assert pipeline.started == 6
        assert pipeline.maximum_active == 5
        assert not service.has_active_jobs()
    finally:
        await service.stop()
