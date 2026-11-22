import json
import sys
from pathlib import Path

import pytest

from voxpull.domain.errors import DependencyMissingError
from voxpull.infrastructure.processes import ProcessResult
from voxpull.infrastructure.transcriber import WhisperCppTranscriber, parse_whisper_json


def test_parses_whisper_json() -> None:
    transcript = parse_whisper_json(
        {
            "result": {"language": "zh"},
            "transcription": [
                {"offsets": {"from": 0, "to": 1200}, "text": " 第一句 "},
                {"offsets": {"from": 1200, "to": 2400}, "text": "這個軟體會將繁體轉為簡體"},
            ],
        }
    )
    assert transcript.detected_language == "zh"
    assert transcript.text == "第一句\n这个软体会将繁体转为简体"
    assert transcript.segments[1].start_ms == 1200


@pytest.mark.parametrize("platform", ["darwin", "win32"])
async def test_transcriber_enables_vad_and_limits_text_context(tmp_path: Path, monkeypatch, platform) -> None:
    from voxpull.infrastructure import transcriber
    monkeypatch.setattr(transcriber.sys, "platform", platform)
    binary = tmp_path / "whisper-cli"
    model = tmp_path / "whisper.bin"
    vad_model = tmp_path / "vad.bin"
    audio = tmp_path / "audio.wav"
    for path in (binary, model, vad_model, audio):
        path.write_bytes(b"test")

    class RecordingRunner:
        command: tuple[str, ...] = ()

        async def run(self, args, *, timeout, on_stderr_line=None, cwd=None) -> ProcessResult:
            self.command = tuple(args)
            output_prefix = Path(self.command[self.command.index("-of") + 1])
            if cwd:
                output_prefix = cwd / output_prefix
                assert (cwd / "model.bin").read_bytes() == b"test"
                assert (cwd / "audio.wav").read_bytes() == b"test"
                assert (cwd / "vad.bin").read_bytes() == b"test"
                assert all(value.isascii() for value in self.command[1:])
            output_prefix.with_suffix(".json").write_text(
                json.dumps(
                    {
                        "result": {"language": "zh"},
                        "transcription": [
                            {"offsets": {"from": 0, "to": 1000}, "text": "正常语音"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            if on_stderr_line is not None:
                on_stderr_line("progress = 25%")
            assert timeout == 30
            return ProcessResult(0, "", "")

    runner = RecordingRunner()
    progress_updates: list[tuple[int, str]] = []
    transcriber = WhisperCppTranscriber(runner, str(binary), model, 30, vad_model)

    transcript = await transcriber.transcribe(
        audio,
        "zh",
        tmp_path,
        lambda value, message: progress_updates.append((value, message)),
    )

    assert transcript.text == "正常语音"
    assert (tmp_path / "transcript.json").is_file()
    assert not list(tmp_path.glob(".voxpull-asr-*"))
    assert ("--vad", "-vm", "vad.bin" if sys.platform == "win32" else str(vad_model)) == runner.command[-3:]
    assert runner.command[runner.command.index("-mc") + 1] == "64"
    assert "-sns" in runner.command
    assert progress_updates == [(25, "正在识别语音")]


async def test_transcriber_rejects_missing_vad_model(tmp_path: Path) -> None:
    binary = tmp_path / "whisper-cli"
    model = tmp_path / "whisper.bin"
    binary.write_bytes(b"test")
    model.write_bytes(b"test")
    transcriber = WhisperCppTranscriber(
        object(),
        str(binary),
        model,
        30,
        tmp_path / "missing-vad.bin",
    )

    with pytest.raises(DependencyMissingError, match="VAD"):
        await transcriber.transcribe(
            tmp_path / "audio.wav",
            "zh",
            tmp_path,
            lambda _value, _message: None,
        )
