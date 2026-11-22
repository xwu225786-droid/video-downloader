"""Opt-in real FFmpeg + whisper.cpp + VAD test, run by Windows CI."""
import os
from pathlib import Path

import pytest

from voxpull.config import Settings
from voxpull.domain.errors import TranscriptionFailedError
from voxpull.infrastructure.audio import FfmpegAudioExtractor
from voxpull.infrastructure.processes import ProcessRunner
from voxpull.infrastructure.transcriber import WhisperCppTranscriber


@pytest.mark.skipif(not os.getenv('VOXPULL_NATIVE_TRANSCRIBE_SAMPLE'), reason='Needs models and sample audio')
async def test_real_native_transcription_with_unicode_paths(tmp_path):
    settings = Settings.from_env()
    folder = tmp_path / '中文 带空格'
    folder.mkdir()
    audio = folder / '音频.wav'
    runner = ProcessRunner()
    try:
        await FfmpegAudioExtractor(runner, settings.ffmpeg_bin, 60).extract(
            Path(os.environ['VOXPULL_NATIVE_TRANSCRIBE_SAMPLE']), audio)
        try:
            transcript = await WhisperCppTranscriber(
                runner, settings.whisper_bin, settings.model_path, 300,
                settings.vad_model_path,
            ).transcribe(audio, 'en', folder, lambda *_: None)
        except TranscriptionFailedError as exc:
            pytest.fail(str(exc.detail), pytrace=False)
        assert 'country' in transcript.text.lower(), transcript.text
        assert transcript.segments and all(segment.end_ms > segment.start_ms for segment in transcript.segments)
        assert (folder / 'transcript.json').is_file()
    finally:
        await runner.close()
