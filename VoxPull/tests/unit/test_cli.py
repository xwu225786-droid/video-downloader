from __future__ import annotations

import json
import sys
import subprocess
from pathlib import Path
from types import SimpleNamespace

from voxpull import cli


def _runtime(tmp_path: Path, *, pid: int = 4321, port: int = 18765) -> cli.RuntimeState:
    return cli.RuntimeState(
        pid=pid,
        host="127.0.0.1",
        port=port,
        started_at="2026-07-13T12:00:00+00:00",
        project_root="/tmp/voxpull",
        log_path=str(tmp_path / "server.log"),
        token="test-token",
    )


def test_help_lists_all_commands(capsys) -> None:
    assert cli.main(["help"]) == 0

    output = capsys.readouterr().out
    for command in ("start", "restart", "status", "stop", "port", "unstall", "help"):
        assert command in output


def test_restart_stops_before_starting(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(cli, "_stop", lambda _args: calls.append("stop") or 0)
    monkeypatch.setattr(cli, "_start", lambda _args: calls.append("start") or 0)

    assert cli.main(["restart"]) == 0
    assert calls == ["stop", "start"]


def test_restart_does_not_start_when_stop_fails(monkeypatch) -> None:
    monkeypatch.setattr(cli, "_stop", lambda _args: 1)
    monkeypatch.setattr(cli, "_start", lambda _args: (_ for _ in ()).throw(AssertionError))

    assert cli.main(["restart"]) == 1


def test_unstall_removes_installed_files(tmp_path, monkeypatch, capsys) -> None:
    project_root = tmp_path / "project"
    python_path = project_root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    python_path.parent.mkdir(parents=True)
    python_path.touch()
    data_path = project_root / "data" / "videos" / "example.mp4"
    data_path.parent.mkdir(parents=True)
    data_path.touch()
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "server.log").touch()
    (state_dir / "server.log.2026-07-12").touch()

    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        return cli.subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(cli, "PROJECT_ROOT", project_root)
    monkeypatch.setenv("VOXPULL_STATE_DIR", str(state_dir))
    monkeypatch.setattr(cli, "_stop", lambda _args: 0)
    monkeypatch.setattr(cli.shutil, "which", lambda _command: "/usr/local/bin/uv")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    assert cli.main(["unstall"]) == 0
    assert commands == [
        [str(python_path), "-m", "playwright", "uninstall"],
        ["/usr/local/bin/uv", "tool", "uninstall", "voxpull"],
    ]
    assert not (project_root / ".venv").exists()
    assert not (state_dir / "server.log").exists()
    assert not (state_dir / "server.log.2026-07-12").exists()
    assert data_path.exists()
    assert "用户数据" in capsys.readouterr().out


def test_port_prints_running_port(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("VOXPULL_STATE_DIR", str(tmp_path))
    state = _runtime(tmp_path)
    cli._write_runtime(state)
    monkeypatch.setattr(cli, "_is_managed_process", lambda candidate: candidate == state)
    monkeypatch.setattr(cli, "_port_is_open", lambda host, port: True)

    assert cli.main(["port"]) == 0
    assert capsys.readouterr().out == "18765\n"


def test_stale_state_is_removed(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("VOXPULL_STATE_DIR", str(tmp_path))
    state = _runtime(tmp_path)
    cli._write_runtime(state)
    monkeypatch.setattr(cli, "_is_managed_process", lambda _candidate: False)

    assert cli.main(["status"]) == 0
    assert capsys.readouterr().out == "VoxPull 状态：已停止\n"
    assert not (tmp_path / "runtime.json").exists()


def test_runtime_file_has_restrictive_permissions(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("VOXPULL_STATE_DIR", str(tmp_path))

    cli._write_runtime(_runtime(tmp_path))

    runtime_path = tmp_path / "runtime.json"
    assert json.loads(runtime_path.read_text(encoding="utf-8"))["pid"] == 4321
    if sys.platform != "win32":
        assert runtime_path.stat().st_mode & 0o777 == 0o600


def test_start_captures_early_process_errors_in_server_log(
    tmp_path, monkeypatch, capsys
) -> None:
    class ExitedProcess:
        pid = 9876

        @staticmethod
        def poll() -> int:
            return 1

    def fake_popen(_command, **kwargs):
        assert kwargs["stderr"] is subprocess.STDOUT
        kwargs["stdout"].write(b"ModuleNotFoundError: No module named 'httpx'\n")
        kwargs["stdout"].flush()
        return ExitedProcess()

    monkeypatch.setenv("VOXPULL_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(cli, "_settings", lambda: SimpleNamespace(host="127.0.0.1", port=18765))
    monkeypatch.setattr(cli, "_port_is_open", lambda _host, _port: False)
    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)

    assert cli.main(["start"]) == 1

    captured = capsys.readouterr()
    assert "VoxPull 启动失败" in captured.err
    assert "ModuleNotFoundError: No module named 'httpx'" in captured.err
    assert "ModuleNotFoundError" in (tmp_path / "server.log").read_text(encoding="utf-8")
    assert not (tmp_path / "runtime.json").exists()


def test_start_prefers_project_virtualenv_for_server(tmp_path, monkeypatch) -> None:
    class RunningProcess:
        pid = 9876

        @staticmethod
        def poll() -> None:
            return None

    project_root = tmp_path / "project"
    project_python = project_root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    project_python.parent.mkdir(parents=True)
    project_python.touch()
    commands: list[list[str]] = []
    port_checks = 0

    def fake_popen(command, **_kwargs):
        commands.append(command)
        return RunningProcess()

    def fake_port_is_open(_host, _port) -> bool:
        nonlocal port_checks
        port_checks += 1
        return port_checks >= 2

    monkeypatch.setenv("VOXPULL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(cli, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(cli, "_settings", lambda: SimpleNamespace(host="127.0.0.1", port=18765))
    monkeypatch.setattr(cli, "_port_is_open", fake_port_is_open)
    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)

    assert cli.main(["start"]) == 0
    assert len(commands) == 1
    assert commands[0][:4] == [str(project_python), "-m", "voxpull", "_serve"]
