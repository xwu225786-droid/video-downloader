from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class JobStage(StrEnum):
    QUEUED = "queued"
    ACQUIRING_COOKIE = "acquiring_cookie"
    DOWNLOADING = "downloading"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class MediaKind(StrEnum):
    VIDEO = "video"
    IMAGES = "images"


class MediaAssetKind(StrEnum):
    IMAGE = "image"
    LIVE_MOTION = "live_motion"


class SummaryStyle(StrEnum):
    BRIEF = "brief"
    DETAILED = "detailed"


@dataclass(frozen=True, slots=True)
class BrowserCookie:
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: float = -1
    http_only: bool = False
    secure: bool = False


@dataclass(frozen=True, slots=True)
class BrowserEvidence:
    final_url: str
    user_agent: str
    cookie_file: Path
    media: MediaMetadata | None = None
    downloaded_video: Path | None = None


DOUYIN_PUBLIC_SHARE_POLICY = "douyin-public-share-v1"
DOUYIN_GUEST_POLICY = "douyin-guest-best-v2"
DOUYIN_INTERNAL_POLICY = "douyin-internal-best-v2"


@dataclass(frozen=True, slots=True)
class ImageAssetMetadata:
    index: int
    source_urls: tuple[str, ...]
    motion_urls: tuple[str, ...] = ()
    width: int | None = None
    height: int | None = None

    @property
    def is_live(self) -> bool:
        return bool(self.motion_urls)


@dataclass(frozen=True, slots=True)
class MediaMetadata:
    id: str
    title: str
    kind: MediaKind = MediaKind.VIDEO
    duration: float | None = None
    source_urls: tuple[str, ...] = ()
    images: tuple[ImageAssetMetadata, ...] = ()
    image_source_policy: str | None = None
    published_at: int | None = None
    video_source_policy: str | None = None
    description: str = ""
    video_width: int | None = None
    video_height: int | None = None
    video_bitrate: int | None = None


@dataclass(frozen=True, slots=True)
class MediaAssetInfo:
    index: int
    kind: MediaAssetKind
    filename: str
    absolute_path: str


@dataclass(frozen=True, slots=True)
class MediaInfo:
    id: str
    title: str
    kind: MediaKind
    filename: str
    absolute_path: str
    saved: bool
    duration: float | None = None
    asset_count: int = 0
    live_photo_count: int = 0
    assets: tuple[MediaAssetInfo, ...] = ()
    cover_path: str | None = None
    title_path: str | None = None
    published_at: int | None = None
    description: str = ""
    description_path: str | None = None
    video_source_policy: str | None = None


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True, slots=True)
class Transcript:
    text: str
    segments: tuple[TranscriptSegment, ...]
    detected_language: str


@dataclass(frozen=True, slots=True)
class VideoSummary:
    markdown: str


@dataclass(frozen=True, slots=True)
class SummaryProviderStatus:
    configured: bool
    base_url: str
    model: str


@dataclass(frozen=True, slots=True)
class JobResult:
    media: MediaInfo
    transcript: Transcript | None = None


@dataclass(frozen=True, slots=True)
class JobErrorInfo:
    code: str
    message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class JobBatch:
    id: str
    job_ids: tuple[str, ...]
    language: str
    save_video: bool
    duplicate_count: int = 0
    extract_txt: bool = True


@dataclass(slots=True)
class Job:
    id: str
    content: str
    language: str
    save_video: bool = True
    status: JobStatus = JobStatus.QUEUED
    stage: JobStage = JobStage.QUEUED
    progress: int = 0
    message: str = "等待处理"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    result: JobResult | None = None
    error: JobErrorInfo | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extract_txt: bool = True


@dataclass(frozen=True, slots=True)
class ComponentStatus:
    ready: bool
    detail: str


@dataclass(frozen=True, slots=True)
class SystemSnapshot:
    python: ComponentStatus
    playwright: ComponentStatus
    chromium: ComponentStatus
    cookie: ComponentStatus
    yt_dlp: ComponentStatus
    ffmpeg: ComponentStatus
    whisper_cpp: ComponentStatus
    model: ComponentStatus
    vad_model: ComponentStatus

    @property
    def ready(self) -> bool:
        return all(
            component.ready
            for component in (
                self.playwright,
                self.chromium,
                self.cookie,
                self.yt_dlp,
                self.ffmpeg,
                self.whisper_cpp,
                self.model,
                self.vad_model,
            )
        )
