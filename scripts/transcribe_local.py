"""Generate durable transcripts from a local media file, without a cloud API."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import tempfile
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from voxpull.application.exporters import to_srt, to_timeline_text
from voxpull.config import Settings
from voxpull.domain.errors import VoxPullError
from voxpull.infrastructure.audio import FfmpegAudioExtractor
from voxpull.infrastructure.processes import ProcessRunner
from voxpull.infrastructure.transcriber import WhisperCppTranscriber


async def transcribe(source: Path, output_root: Path, language: str) -> Path:
    settings = Settings.from_env()
    runner = ProcessRunner()
    output_root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="transcribe-", dir=output_root) as temporary:
            work_dir = Path(temporary)
            audio = work_dir / "audio.wav"
            print("正在本机提取音频……", flush=True)
            await FfmpegAudioExtractor(
                runner, settings.ffmpeg_bin, settings.ffmpeg_timeout_seconds
            ).extract(source, audio)
            print("正在本机识别语音……", flush=True)
            engine = WhisperCppTranscriber(
                runner, settings.whisper_bin, settings.model_path,
                settings.whisper_timeout_seconds, settings.vad_model_path,
            )
            last_progress = -1

            def progress(value: int, message: str) -> None:
                nonlocal last_progress
                if value >= last_progress + 10 or value == 100:
                    print(f"{message}：{value}%", flush=True)
                    last_progress = value

            transcript = await engine.transcribe(audio, language, work_dir, progress)
            if not transcript.segments:
                raise ValueError("未识别到说话内容；请确认文件有人声。")
            stem = re.sub(r'[\x00-\x1f/\\:]', "_", source.stem)[:80] or "视频"
            stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
            output = output_root / f"{stem}_{stamp}_{uuid.uuid4().hex[:6]}"
            output.mkdir()
            (output / "逐字稿.txt").write_text(transcript.text + "\n", encoding="utf-8")
            (output / "时间轴.txt").write_text(to_timeline_text(transcript) + "\n", encoding="utf-8")
            (output / "字幕.srt").write_text(to_srt(transcript), encoding="utf-8")
            payload = {
                "source_file": str(source),
                "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                "engine": "whisper.cpp", "model": settings.model_path.name,
                "language": transcript.detected_language,
                "text": transcript.text,
                "segments": [asdict(segment) for segment in transcript.segments],
                "note": "本地自动识别原始稿，未经总结或改写，可能存在听写错误。",
            }
            (output / "识别结果.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            return output
    finally:
        await runner.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="在本机将音视频转为逐字稿、时间轴和字幕")
    parser.add_argument("file", type=Path)
    parser.add_argument("--language", default="zh", help="默认中文；可用 auto 或 en")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "逐字稿")
    args = parser.parse_args()
    source = args.file.expanduser().resolve()
    if not source.is_file():
        parser.error(f"文件不存在：{source}")
    try:
        output = asyncio.run(transcribe(source, args.output_dir.expanduser().resolve(), args.language))
    except (VoxPullError, OSError, ValueError) as exc:
        print(f"转写失败：{exc}", file=sys.stderr)
        detail = getattr(exc, "detail", None)
        if detail:
            print(detail, file=sys.stderr)
        return 1
    print(f"已保存到：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
