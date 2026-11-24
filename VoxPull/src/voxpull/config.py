from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value).expanduser().resolve() if value else default.resolve()


@dataclass(frozen=True, slots=True)
class Settings:
    host: str
    port: int
    data_dir: Path
    ffmpeg_bin: str
    max_queue: int
    browser_timeout_seconds: float
    download_timeout_seconds: float
    ffmpeg_timeout_seconds: float
    max_concurrency: int = 5
    download_concurrency: int = 5
    ffmpeg_concurrency: int = 2
    transcription_concurrency: int = 2
    summary_timeout_seconds: float = 180
    summary_concurrency: int = 2
    summary_max_input_chars: int = 200_000

    @property
    def auth_dir(self) -> Path:
        return self.data_dir / "auth"

    @property
    def storage_state_path(self) -> Path:
        return self.auth_dir / "storage-state.json"

    @property
    def deepseek_auth_path(self) -> Path:
        return self.auth_dir / "deepseek-auth.json"

    @property
    def summary_auth_path(self) -> Path:
        return self.auth_dir / "summary-auth.json"

    @property
    def storage_location_path(self) -> Path:
        return self.data_dir / "storage-location.json"

    @property
    def browser_profile_dir(self) -> Path:
        return _env_path("VOXPULL_BROWSER_PROFILE_DIR", self.data_dir / "browser-profile")

    @property
    def videos_dir(self) -> Path:
        return self.data_dir / "videos"

    @property
    def images_dir(self) -> Path:
        return self.data_dir / "images"

    @property
    def work_dir(self) -> Path:
        return self.data_dir / "work"

    @property
    def web_dir(self) -> Path:
        return Path(__file__).resolve().parent / "web"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            host=os.getenv("VOXPULL_HOST", "127.0.0.1"),
            port=int(os.getenv("VOXPULL_PORT", "18765")),
            data_dir=_env_path("VOXPULL_DATA_DIR", PROJECT_ROOT / "data"),
            ffmpeg_bin=os.getenv("VOXPULL_FFMPEG_BIN", "ffmpeg"),
            max_queue=max(1, int(os.getenv("VOXPULL_MAX_QUEUE", "10"))),
            browser_timeout_seconds=float(os.getenv("VOXPULL_BROWSER_TIMEOUT", "120")),
            download_timeout_seconds=float(os.getenv("VOXPULL_DOWNLOAD_TIMEOUT", "900")),
            ffmpeg_timeout_seconds=float(os.getenv("VOXPULL_FFMPEG_TIMEOUT", "900")),
            max_concurrency=max(1, int(os.getenv("VOXPULL_MAX_CONCURRENCY", "5"))),
            download_concurrency=max(1, int(os.getenv("VOXPULL_DOWNLOAD_CONCURRENCY", "5"))),
            ffmpeg_concurrency=max(1, int(os.getenv("VOXPULL_FFMPEG_CONCURRENCY", "2"))),
            transcription_concurrency=max(1, int(os.getenv("VOXPULL_TRANSCRIPTION_CONCURRENCY", "2"))),
            summary_timeout_seconds=float(os.getenv("VOXPULL_SUMMARY_TIMEOUT", "180")),
            summary_concurrency=max(1, int(os.getenv("VOXPULL_SUMMARY_CONCURRENCY", "2"))),
            summary_max_input_chars=max(
                1, int(os.getenv("VOXPULL_SUMMARY_MAX_INPUT_CHARS", "200000"))
            ),
        )

    def ensure_directories(self) -> None:
        for path in (
            self.auth_dir,
            self.browser_profile_dir,
            self.videos_dir,
            self.images_dir,
            self.work_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
