from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from voxpull.domain.models import (
    BrowserEvidence,
    Job,
    MediaMetadata,
    SummaryProviderStatus,
    SummaryStyle,
    SystemSnapshot,
    Transcript,
    VideoSummary,
)


ProgressCallback = Callable[[int, str], None]


class BrowserPort(Protocol):
    async def start_auth(self, target_url: str | None = None) -> str: ...

    async def complete_auth(self) -> str: ...

    async def auth_status(self) -> str: ...

    async def import_chrome_cookies(self) -> str: ...

    async def acquire(self, url: str, cookie_file: Path, *,
                      on_state: Callable[[str, str], None] | None = None) -> BrowserEvidence: ...

    async def close(self) -> None: ...


class GuestReaderPort(Protocol):
    async def acquire(self, url: str, cookie_file: Path, *,
                      on_state: Callable[[str, str], None] | None = None) -> BrowserEvidence | None: ...

    async def close(self) -> None: ...


class DownloaderPort(Protocol):
    async def probe(self, url: str, cookie_file: Path, user_agent: str) -> MediaMetadata: ...

    async def download(
        self,
        url: str,
        metadata: MediaMetadata,
        cookie_file: Path,
        user_agent: str,
        work_dir: Path,
        progress: ProgressCallback,
    ) -> Path: ...

    async def download_images(
        self,
        url: str,
        metadata: MediaMetadata,
        cookie_file: Path,
        user_agent: str,
        work_dir: Path,
        progress: ProgressCallback,
    ) -> Path: ...


class AudioExtractorPort(Protocol):
    async def extract(self, video_path: Path, audio_path: Path) -> None: ...


class CoverExtractorPort(Protocol):
    async def extract(self, video_path: Path, cover_path: Path) -> None: ...


class TranscriberPort(Protocol):
    async def transcribe(
        self, audio_path: Path, language: str, work_dir: Path, progress: ProgressCallback
    ) -> Transcript: ...


class StoragePort(Protocol):
    def create_work_dir(self, job_id: str) -> Path: ...

    def prepare_material(self, media_id: str, title: str, kind: str) -> Path: ...

    def save_material_text(
        self, media_id: str, title: str, kind: str, *,
        description: str = "", transcript: str | None = None,
    ) -> tuple[Path, Path | None]: ...

    def find_video(self, video_id: str) -> Path | None: ...

    def publish_video(self, source: Path, video_id: str) -> Path: ...

    def publish_video_details(
        self, cover: Path, title: str, video_id: str
    ) -> tuple[Path, Path]: ...

    def find_image_folder(
        self,
        media_id: str,
        *,
        source_policy: str | None = None,
    ) -> Path | None: ...

    def publish_image_folder(self, source: Path, media_id: str) -> Path: ...

    def name_gallery_files(self, folder: Path) -> Path | None: ...

    def cleanup_work_dir(self, job_id: str) -> None: ...

    def cleanup_stale_work_dirs(self, max_age_hours: int = 24) -> int: ...


class JobRepositoryPort(Protocol):
    def add(self, job: Job) -> None: ...

    def get(self, job_id: str) -> Job | None: ...

    def update(self, job_id: str, **changes: object) -> Job: ...


class SummarizerPort(Protocol):
    async def summarize(
        self,
        text: str,
        style: SummaryStyle,
    ) -> VideoSummary: ...

    async def list_models(self, base_url: str, api_key: str) -> list[str]: ...


class SummaryConfiguratorPort(Protocol):
    def status(self) -> SummaryProviderStatus: ...

    async def configure(self, base_url: str, api_key: str, model: str) -> None: ...

    async def clear(self) -> None: ...


class SystemProbePort(Protocol):
    async def inspect(self, cookie_status: str) -> SystemSnapshot: ...
