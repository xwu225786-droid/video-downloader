from __future__ import annotations

import shutil
from pathlib import Path

from voxpull.domain.errors import AudioExtractionFailedError, DependencyMissingError
from voxpull.infrastructure.processes import ProcessRunner


class FfmpegAudioExtractor:
    def __init__(self, runner: ProcessRunner, binary: str, timeout: float) -> None:
        self.runner = runner
        self.binary = binary
        self.timeout = timeout

    async def extract(self, video_path: Path, audio_path: Path) -> None:
        if not shutil.which(self.binary) and not Path(self.binary).is_file():
            raise DependencyMissingError(f"找不到 ffmpeg：{self.binary}")
        result = await self.runner.run(
            (
                self.binary,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(video_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(audio_path),
            ),
            timeout=self.timeout,
        )
        if result.returncode != 0 or not audio_path.is_file() or audio_path.stat().st_size == 0:
            raise AudioExtractionFailedError(detail=result.stderr[-4000:])
