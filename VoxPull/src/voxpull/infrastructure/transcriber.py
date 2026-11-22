from __future__ import annotations

import json
import re
import shutil
from functools import lru_cache
from pathlib import Path

from opencc import OpenCC

from voxpull.domain.errors import DependencyMissingError, TranscriptionFailedError
from voxpull.domain.models import Transcript, TranscriptSegment
from voxpull.domain.ports import ProgressCallback
from voxpull.infrastructure.processes import ProcessRunner


_PROGRESS_RE = re.compile(r"progress\s*=\s*(\d+)%")


class WhisperCppTranscriber:
    def __init__(
        self,
        runner: ProcessRunner,
        binary: str,
        model_path: Path,
        timeout: float,
        vad_model_path: Path | None = None,
    ) -> None:
        self.runner = runner
        self.binary = binary
        self.model_path = model_path
        self.timeout = timeout
        self.vad_model_path = vad_model_path

    async def transcribe(
        self, audio_path: Path, language: str, work_dir: Path, progress: ProgressCallback
    ) -> Transcript:
        if not shutil.which(self.binary) and not Path(self.binary).is_file():
            raise DependencyMissingError(f"找不到 whisper-cli：{self.binary}")
        if not self.model_path.is_file():
            raise DependencyMissingError(f"找不到 Whisper 模型：{self.model_path}")
        if self.vad_model_path is not None and not self.vad_model_path.is_file():
            raise DependencyMissingError(f"找不到 VAD 模型：{self.vad_model_path}")

        output_prefix = work_dir / "transcript"

        def on_line(line: str) -> None:
            if match := _PROGRESS_RE.search(line):
                progress(min(100, int(match.group(1))), "正在识别语音")

        command = [
            self.binary,
            "-m",
            str(self.model_path),
            "-f",
            str(audio_path),
            "-l",
            language,
            "-oj",
            "-of",
            str(output_prefix),
            "-pp",
            "-sns",
            "-mc",
            "64",
        ]
        if self.vad_model_path is not None:
            command.extend(("--vad", "-vm", str(self.vad_model_path)))

        result = await self.runner.run(
            command,
            timeout=self.timeout,
            on_stderr_line=on_line,
        )
        output_path = output_prefix.with_suffix(".json")
        if result.returncode != 0 or not output_path.is_file():
            raise TranscriptionFailedError(detail=result.stderr[-4000:])
        try:
            return parse_whisper_json(json.loads(output_path.read_text(encoding="utf-8")))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise TranscriptionFailedError("无法解析 whisper.cpp 的输出", detail=str(exc)) from exc


def parse_whisper_json(payload: dict[str, object]) -> Transcript:
    result = payload.get("result")
    detected_language = (
        str(result.get("language", "unknown")) if isinstance(result, dict) else "unknown"
    )
    raw_segments = payload.get("transcription")
    if not isinstance(raw_segments, list):
        raise ValueError("transcription must be a list")
    segments: list[TranscriptSegment] = []
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        offsets = item.get("offsets")
        if not isinstance(offsets, dict):
            continue
        text = _to_simplified_chinese(str(item.get("text", "")).strip())
        if not text:
            continue
        segments.append(
            TranscriptSegment(
                start_ms=int(offsets.get("from", 0)),
                end_ms=int(offsets.get("to", 0)),
                text=text,
            )
        )
    return Transcript(
        text="\n".join(segment.text for segment in segments),
        segments=tuple(segments),
        detected_language=detected_language,
    )


@lru_cache(maxsize=1)
def _simplified_chinese_converter() -> OpenCC:
    return OpenCC("t2s")


def _to_simplified_chinese(text: str) -> str:
    """Normalize Whisper output so every result and export uses Simplified Chinese."""
    return _simplified_chinese_converter().convert(text)
