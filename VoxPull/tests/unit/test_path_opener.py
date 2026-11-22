from __future__ import annotations

import subprocess

import pytest

from voxpull.infrastructure import path_opener
from voxpull.infrastructure.path_opener import NativePathOpener


@pytest.mark.parametrize(
    ("is_directory", "expected_prefix"),
    [(True, ["open", "-R"]), (False, ["open", "-R"])],
)
def test_macos_path_opener_reveals_saved_media(
    tmp_path,
    monkeypatch,
    is_directory: bool,
    expected_prefix: list[str],
) -> None:
    target = tmp_path / ("gallery" if is_directory else "video.mp4")
    if is_directory:
        target.mkdir()
    else:
        target.write_bytes(b"video")
    commands: list[list[str]] = []

    def record_run(command: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(path_opener.sys, "platform", "darwin")
    monkeypatch.setattr(path_opener.subprocess, "run", record_run)

    NativePathOpener()._reveal_sync(target)

    assert commands == [[*expected_prefix, str(target.resolve())]]
