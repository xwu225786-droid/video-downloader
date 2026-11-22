from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from voxpull.domain.models import Job, JobBatch, JobStatus, MediaAssetKind, SummaryStyle, VideoSummary


class ErrorResponse(BaseModel):
    code: str
    message: str
    retryable: bool = False


class AuthStatusResponse(BaseModel):
    status: str
    target_url: str | None = None
    waiting_jobs: int = 0
    session_shared: bool = False
    active_job: bool = False


class SystemComponent(BaseModel):
    ready: bool
    detail: str


class SystemStatusResponse(BaseModel):
    ready: bool
    video_storage_path: str
    image_storage_path: str
    python: SystemComponent
    playwright: SystemComponent
    chromium: SystemComponent
    cookie: SystemComponent
    yt_dlp: SystemComponent
    ffmpeg: SystemComponent
    whisper_cpp: SystemComponent
    model: SystemComponent
    vad_model: SystemComponent


class StorageLocationResponse(BaseModel):
    changed: bool
    media_root_path: str
    video_storage_path: str
    image_storage_path: str


class OpenLocationResponse(BaseModel):
    opened: bool


class SummaryConfigRequest(BaseModel):
    base_url: str
    api_key: str
    model: str


class SummaryConfigResponse(BaseModel):
    configured: bool
    base_url: str
    model: str


class SummaryModelsRequest(BaseModel):
    base_url: str
    api_key: str = ""


class SummaryModelsResponse(BaseModel):
    models: list[str]


class SummaryGenerateRequest(BaseModel):
    style: str = "brief"
    transcript_text: str


class VideoSummaryResponse(BaseModel):
    markdown: str
    style: SummaryStyle
    model: str
    generated_at: datetime

    @classmethod
    def from_domain(cls, summary: VideoSummary, style: SummaryStyle, model: str) -> "VideoSummaryResponse":
        return cls(
            markdown=summary.markdown,
            style=style,
            model=model,
            generated_at=datetime.now(UTC),
        )


class JobCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4096)
    language: Literal["zh", "auto"] = "zh"
    save_video: bool = True
    extract_txt: bool = True
    auto_summary: bool = False


class JobAcceptedResponse(BaseModel):
    job_id: str
    status: str
    queued_ahead: int


class BatchCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    language: Literal["zh", "auto"] = "zh"
    save_video: bool = True
    extract_txt: bool = True
    auto_summary: bool = False


class BatchItemResponse(BaseModel):
    id: str
    source_url: str
    status: str
    progress: int
    message: str
    title: str | None
    result_available: bool
    subtitle_completed: bool = False
    summary_completed: bool = False
    subtitle_state: str = "not_requested"
    summary_state: str = "not_requested"
    auth_status: str | None = None
    error: ErrorResponse | None = None


class BatchResponse(BaseModel):
    id: str
    status: str
    total: int
    queued: int
    running: int
    completed: int
    failed: int
    paused: int = 0
    progress: int
    duplicate_count: int
    jobs: list[BatchItemResponse]


def processing_states(job: Job) -> dict[str, str]:
    subtitle = "completed" if job.result and job.result.transcript is not None else (
        "generating" if job.extract_txt and job.status in {JobStatus.RUNNING, JobStatus.QUEUED}
        else "failed" if job.extract_txt and job.status is JobStatus.FAILED else "not_requested")
    summary = job.metadata.get("summary_state") or ("completed" if job.metadata.get("ai_summary") else (
        "waiting" if job.metadata.get("auto_summary") and job.status in {JobStatus.RUNNING, JobStatus.QUEUED}
        else "not_requested"))
    return {"subtitle_state": subtitle, "summary_state": summary}


def batch_to_response(batch: JobBatch, jobs: list[Job]) -> BatchResponse:
    counts = {state.value: sum(job.status is state for job in jobs) for state in JobStatus}
    done = counts["completed"] + counts["failed"] + counts["paused"] == len(jobs)
    state = "running" if any(counts[key] for key in ("running", "completed", "failed", "paused")) else "queued"
    if done:
        state = "completed" if not counts["failed"] else "completed_with_errors"
        if counts["paused"] and not counts["failed"]:
            state = "paused"
    return BatchResponse(
        id=batch.id, status=state, total=len(jobs),
        queued=counts["queued"], running=counts["running"],
        completed=counts["completed"], failed=counts["failed"],
        paused=counts["paused"],
        progress=sum(100 if job.status in {JobStatus.FAILED, JobStatus.PAUSED} else job.progress for job in jobs) // max(1, len(jobs)),
        duplicate_count=batch.duplicate_count,
        jobs=[BatchItemResponse(
            id=job.id, source_url=job.content, status=job.status.value,
            progress=job.progress, message=job.message,
            title=job.result.media.title if job.result else job.metadata.get("title"),
            result_available=job.result is not None,
            subtitle_completed=bool(job.result and job.result.transcript is not None),
            summary_completed=bool(job.metadata.get("ai_summary")),
            **processing_states(job),
            auth_status=job.metadata.get("auth_status") or None,
            error=ErrorResponse(code=job.error.code, message=job.error.message, retryable=job.error.retryable)
            if job.error else None,
        ) for job in jobs],
    )


class SegmentResponse(BaseModel):
    start_ms: int
    end_ms: int
    text: str


class TranscriptResponse(BaseModel):
    text: str
    detected_language: str
    segments: list[SegmentResponse]


class MediaAssetResponse(BaseModel):
    index: int
    kind: str
    filename: str
    absolute_path: str
    preview_url: str | None = None
    playback_url: str | None = None


class MediaResponse(BaseModel):
    id: str
    title: str
    kind: str
    filename: str
    absolute_path: str
    saved: bool
    duration: float | None
    asset_count: int
    live_photo_count: int
    assets: list[MediaAssetResponse]
    cover_path: str | None = None
    cover_url: str | None = None
    title_path: str | None = None
    title_url: str | None = None
    video_url: str | None = None
    published_at: int | None = None
    publication_url: str | None = None
    description: str = ""
    description_path: str | None = None


class JobResultResponse(BaseModel):
    media: MediaResponse
    transcript: TranscriptResponse | None = None


class SavedSummaryResponse(BaseModel):
    markdown: str
    source_text: str
    model: str
    style: str
    generated_at: str


class JobResponse(BaseModel):
    auth_status: str | None = None
    id: str
    status: str
    stage: str
    progress: int
    message: str
    created_at: datetime
    result: JobResultResponse | None = None
    error: ErrorResponse | None = None
    summary: SavedSummaryResponse | None = None
    subtitle_state: str = "not_requested"
    summary_state: str = "not_requested"


def job_to_response(job: Job) -> JobResponse:
    result = None
    if job.result is not None:
        result = JobResultResponse(
            media=MediaResponse(
                id=job.result.media.id,
                title=job.result.media.title,
                kind=job.result.media.kind.value,
                filename=job.result.media.filename,
                absolute_path=job.result.media.absolute_path,
                saved=job.result.media.saved,
                duration=job.result.media.duration,
                asset_count=job.result.media.asset_count,
                live_photo_count=job.result.media.live_photo_count,
                cover_path=job.result.media.cover_path,
                cover_url=f"/api/jobs/{job.id}/cover" if job.result.media.cover_path else None,
                title_path=job.result.media.title_path,
                title_url=f"/api/jobs/{job.id}/title" if job.result.media.title_path else None,
                video_url=f"/api/jobs/{job.id}/video"
                if job.result.media.kind.value == "video" and (job.result.media.saved or (
                    job.status is JobStatus.RUNNING and Path(job.result.media.absolute_path).is_file())) else None,
                published_at=job.result.media.published_at,
                description=job.result.media.description,
                description_path=job.result.media.description_path,
                publication_url=f"/api/jobs/{job.id}/publication",
                assets=[
                    MediaAssetResponse(
                        index=asset.index,
                        kind=asset.kind.value,
                        filename=asset.filename,
                        absolute_path=asset.absolute_path,
                        preview_url=(
                            f"/api/jobs/{job.id}/assets/{position}"
                            if asset.kind is MediaAssetKind.IMAGE
                            else None
                        ),
                        playback_url=(
                            f"/api/jobs/{job.id}/assets/{position}"
                            if asset.kind is MediaAssetKind.LIVE_MOTION
                            else None
                        ),
                    )
                    for position, asset in enumerate(job.result.media.assets)
                ],
            ),
            transcript=(
                TranscriptResponse(
                    text=job.result.transcript.text,
                    detected_language=job.result.transcript.detected_language,
                    segments=[
                        SegmentResponse(
                            start_ms=segment.start_ms,
                            end_ms=segment.end_ms,
                            text=segment.text,
                        )
                        for segment in job.result.transcript.segments
                    ],
                )
                if job.result.transcript is not None
                else None
            ),
        )
    error = (
        ErrorResponse(
            code=job.error.code,
            message=job.error.message,
            retryable=job.error.retryable,
        )
        if job.error
        else None
    )
    return JobResponse(
        auth_status=job.metadata.get("auth_status") or None,
        id=job.id,
        status=job.status.value,
        stage=job.stage.value,
        progress=job.progress,
        message=job.message,
        created_at=job.created_at,
        result=result,
        error=error,
        summary=job.metadata.get("ai_summary"),
        **processing_states(job),
    )
