from __future__ import annotations

import shutil
from pathlib import Path

from voxpull.domain.errors import CoverExtractionFailedError, DependencyMissingError
from voxpull.infrastructure.processes import ProcessRunner


class FfmpegCoverExtractor:
    """Extract the first decoded video frame, rather than a platform thumbnail."""

    def __init__(self, runner: ProcessRunner, binary: str, timeout: float) -> None:
        self.runner = runner
        self.binary = binary
        self.timeout = timeout

    async def extract(self, video_path: Path, cover_path: Path) -> None:
        if not shutil.which(self.binary) and not Path(self.binary).is_file():
            raise DependencyMissingError(f"找不到 ffmpeg：{self.binary}")
        result = await self.runner.run(
            (
                self.binary, "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(video_path), "-map", "0:v:0", "-frames:v", "1",
                "-q:v", "2", "-update", "1", str(cover_path),
            ),
            timeout=self.timeout,
        )
        if result.returncode != 0 or not cover_path.is_file() or cover_path.stat().st_size == 0:
            raise CoverExtractionFailedError(detail=result.stderr[-4000:])
