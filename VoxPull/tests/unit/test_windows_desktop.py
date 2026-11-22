import subprocess

import pytest

from voxpull.infrastructure import directory_picker, path_opener


def test_windows_directory_picker_keeps_unicode_and_escapes_quotes(tmp_path, monkeypatch):
    initial = tmp_path / "中文 O'Brien"
    chosen = tmp_path / '选中 目录'
    def run(command, **kwargs):
        assert command[:4] == ['powershell.exe', '-NoProfile', '-STA', '-Command']
        assert "O''Brien" in command[4]
        assert kwargs['encoding'] == 'utf-8'
        return subprocess.CompletedProcess(command, 0, str(chosen) + '\n', '')
    monkeypatch.setattr(directory_picker.subprocess, 'run', run)
    assert directory_picker._choose_windows(initial) == chosen.resolve()


def test_windows_directory_picker_cancel_and_error(tmp_path, monkeypatch):
    monkeypatch.setattr(directory_picker.subprocess, 'run',
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, '', ''))
    assert directory_picker._choose_windows(tmp_path) is None
    monkeypatch.setattr(directory_picker.subprocess, 'run',
                        lambda *a, **k: subprocess.CompletedProcess(a, 1, '', 'unavailable'))
    with pytest.raises(directory_picker.DirectoryPickerError, match='unavailable'):
        directory_picker._choose_windows(tmp_path)


def test_windows_reveal_dispatches_unicode_path_to_explorer(tmp_path, monkeypatch):
    target = tmp_path / '中文 视频.mp4'
    target.touch()
    calls = []
    monkeypatch.setattr(path_opener.sys, 'platform', 'win32')
    monkeypatch.setattr(path_opener.subprocess, 'Popen', lambda command, **_: calls.append(command))
    path_opener.NativePathOpener()._reveal_sync(target)
    assert calls == [['explorer.exe', '/select,', str(target.resolve())]]
