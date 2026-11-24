from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Sequence

from voxpull.infrastructure.file_lock import lock_file, unlock_file

from voxpull.config import PROJECT_ROOT, Settings


START_TIMEOUT_SECONDS = 15.0
STOP_TIMEOUT_SECONDS = 10.0
POLL_INTERVAL_SECONDS = 0.1


@dataclass(frozen=True, slots=True)
class RuntimeState:
    pid: int
    host: str
    port: int
    started_at: str
    project_root: str
    log_path: str
    token: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuntimeState:
        state = cls(
            pid=int(data["pid"]),
            host=str(data["host"]),
            port=int(data["port"]),
            started_at=str(data["started_at"]),
            project_root=str(data["project_root"]),
            log_path=str(data["log_path"]),
            token=str(data["token"]),
        )
        if state.pid <= 0 or not 1 <= state.port <= 65535 or not state.token:
            raise ValueError("invalid runtime state")
        return state


def _state_dir() -> Path:
    configured = os.getenv("VOXPULL_STATE_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    if sys.platform == "win32":
        return Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "VoxPull" / "state"
    xdg_state_home = os.getenv("XDG_STATE_HOME")
    if xdg_state_home:
        return Path(xdg_state_home).expanduser().resolve() / "voxpull"
    return Path.home() / ".local" / "state" / "voxpull"


def _runtime_path() -> Path:
    return _state_dir() / "runtime.json"


def _log_path() -> Path:
    return _state_dir() / "server.log"


@contextmanager
def _command_lock() -> Iterator[None]:
    state_dir = _state_dir()
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state_dir / "command.lock").open("a+", encoding="utf-8") as handle:
        lock_file(handle)
        try:
            yield
        finally:
            unlock_file(handle)


def _read_runtime() -> RuntimeState | None:
    try:
        data = json.loads(_runtime_path().read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return RuntimeState.from_dict(data)
    except KeyError, OSError, TypeError, ValueError, json.JSONDecodeError:
        return None


def _write_runtime(state: RuntimeState) -> None:
    path = _runtime_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary_path = path.with_suffix(f".{os.getpid()}.tmp")
    temporary_path.write_text(
        json.dumps(asdict(state), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.chmod(0o600)
    temporary_path.replace(path)


def _remove_runtime() -> None:
    with contextlib.suppress(FileNotFoundError):
        _runtime_path().unlink()


def _process_command(pid: int) -> str | None:
    if sys.platform == "win32":
        # A PID alone is unsafe: Windows may already have reused it. Check the
        # command line and the per-start random token before stopping anything.
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                 "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); "
                 f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)}').CommandLine"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                check=False, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat=", "-o", "command="],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except OSError, subprocess.SubprocessError:
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    status_and_command = result.stdout.strip().split(maxsplit=1)
    if len(status_and_command) != 2 or "Z" in status_and_command[0]:
        return None
    return status_and_command[1]


def _is_managed_process(state: RuntimeState) -> bool:
    command = _process_command(state.pid)
    if command is None:
        return False
    marker = re.compile(r"(?:^|\s)-m\s+voxpull\s+_serve(?:\s|$)")
    return marker.search(command) is not None and state.token in command


def _current_runtime(*, clean_stale: bool = True) -> RuntimeState | None:
    state = _read_runtime()
    if state is not None and _is_managed_process(state):
        return state
    if clean_stale:
        _remove_runtime()
    return None


def _connect_host(host: str) -> str:
    if host == "0.0.0.0":
        return "127.0.0.1"
    if host == "::":
        return "::1"
    return host


def _port_is_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((_connect_host(host), port), timeout=0.25):
            return True
    except OSError:
        return False


def _service_url(host: str, port: int) -> str:
    display_host = _connect_host(host)
    if ":" in display_host:
        display_host = f"[{display_host}]"
    return f"http://{display_host}:{port}"


def _settings() -> Settings | None:
    try:
        settings = Settings.from_env()
    except (OSError, ValueError) as exc:
        print(f"VoxPull 配置无效：{exc}", file=sys.stderr)
        return None
    if not 1 <= settings.port <= 65535:
        print("VoxPull 配置无效：VOXPULL_PORT 必须在 1 到 65535 之间", file=sys.stderr)
        return None
    return settings


def _print_runtime(state: RuntimeState, status: str) -> None:
    print(f"VoxPull 状态：{status}")
    print(f"PID：{state.pid}")
    print(f"端口：{state.port}")
    print(f"地址：{_service_url(state.host, state.port)}")
    print(f"日志：{state.log_path}")


def _log_tail(path: Path, limit: int = 12) -> str:
    try:
        with path.open("rb") as log_file:
            log_file.seek(0, os.SEEK_END)
            size = log_file.tell()
            log_file.seek(max(0, size - 16_384))
            text = log_file.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(text.splitlines()[-limit:])


def _wait_for_exit(state: RuntimeState, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _is_managed_process(state):
            return True
        time.sleep(POLL_INTERVAL_SECONDS)
    return not _is_managed_process(state)


def _terminate(state: RuntimeState) -> bool:
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill.exe", "/PID", str(state.pid), "/T", "/F"],
                capture_output=True, check=False, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return _wait_for_exit(state, 5.0)
    try:
        os.kill(state.pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    if _wait_for_exit(state, STOP_TIMEOUT_SECONDS):
        return True
    try:
        os.kill(state.pid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return _wait_for_exit(state, 2.0)


def _project_python() -> Path:
    if sys.platform == "win32":
        return PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    return PROJECT_ROOT / ".venv" / "bin" / "python"


def _background_options() -> dict[str, Any]:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _start(_args: argparse.Namespace) -> int:
    settings = _settings()
    if settings is None:
        return 2

    with _command_lock():
        current = _current_runtime()
        if current is not None:
            if _port_is_open(current.host, current.port):
                print("VoxPull 已在运行。")
                _print_runtime(current, "运行中")
                return 0
            print(
                "VoxPull 后台进程存在，但端口尚未响应；请先执行 vox status 或 vox stop。",
                file=sys.stderr,
            )
            return 1

        if _port_is_open(settings.host, settings.port):
            print(
                f"无法启动：端口 {settings.port} 已被其他程序占用。",
                file=sys.stderr,
            )
            return 1

        log_path = _log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        token = secrets.token_hex(16)
        project_python = _project_python()
        server_python = project_python if project_python.is_file() else Path(sys.executable)
        command = [str(server_python), "-m", "voxpull", "_serve", token]
        environment = os.environ.copy()
        environment["VOXPULL_LOG_PATH"] = str(log_path)

        try:
            # Keep interpreter/import failures in the same file as application
            # logs. Those failures happen before logging is fully configured, so
            # sending stderr to DEVNULL would leave only the startup marker and
            # hide the actual cause from `vox start`.
            with log_path.open("ab") as startup_log:
                process = subprocess.Popen(
                    command,
                    cwd=PROJECT_ROOT,
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=startup_log,
                    stderr=subprocess.STDOUT,
                    **_background_options(),
                    close_fds=True,
                )
        except OSError as exc:
            print(f"VoxPull 启动失败：{exc}", file=sys.stderr)
            return 1

        state = RuntimeState(
            pid=process.pid,
            host=settings.host,
            port=settings.port,
            started_at=datetime.now(UTC).isoformat(),
            project_root=str(PROJECT_ROOT),
            log_path=str(log_path),
            token=token,
        )
        _write_runtime(state)

        deadline = time.monotonic() + START_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            if _port_is_open(state.host, state.port):
                print("VoxPull 已启动并在后台运行。")
                _print_runtime(state, "运行中")
                return 0
            time.sleep(POLL_INTERVAL_SECONDS)

        if process.poll() is None:
            _terminate(state)
        _remove_runtime()
        print("VoxPull 启动失败。", file=sys.stderr)
        tail = _log_tail(log_path)
        if tail:
            print("日志最后内容：", file=sys.stderr)
            print(tail, file=sys.stderr)
        return 1


def _status(_args: argparse.Namespace) -> int:
    with _command_lock():
        state = _current_runtime()
        if state is None:
            print("VoxPull 状态：已停止")
            return 0
        status = "运行中" if _port_is_open(state.host, state.port) else "进程存在，端口未响应"
        _print_runtime(state, status)
        return 0


def _stop(_args: argparse.Namespace) -> int:
    with _command_lock():
        state = _current_runtime()
        if state is None:
            print("VoxPull 已停止，无需重复操作。")
            return 0
        if not _terminate(state):
            print(f"无法停止 VoxPull 进程（PID {state.pid}）。", file=sys.stderr)
            return 1
        _remove_runtime()
        print("VoxPull 已停止。")
        return 0


def _restart(args: argparse.Namespace) -> int:
    stop_result = _stop(args)
    if stop_result != 0:
        return stop_result
    return _start(args)


def _port(_args: argparse.Namespace) -> int:
    with _command_lock():
        state = _current_runtime()
        if state is None or not _port_is_open(state.host, state.port):
            print("VoxPull 未运行。", file=sys.stderr)
            return 1
        print(state.port)
        return 0


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _uninstall_playwright() -> bool:
    python_path = _project_python()
    if not python_path.is_file():
        return True

    try:
        result = subprocess.run(
            [str(python_path), "-m", "playwright", "uninstall"],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"无法卸载 Playwright 浏览器：{exc}", file=sys.stderr)
        return False

    if result.returncode == 0:
        return True
    detail = result.stderr.strip() or result.stdout.strip()
    suffix = f"：{detail}" if detail else ""
    print(f"无法卸载 Playwright 浏览器{suffix}", file=sys.stderr)
    return False


def _remove_installation_files() -> bool:
    log_paths = tuple(sorted(_state_dir().glob(f"{_log_path().name}*")))
    paths = (
        PROJECT_ROOT / ".venv",
        _runtime_path(),
        *log_paths,
        _state_dir() / "command.lock",
    )
    success = True
    for path in paths:
        try:
            _remove_path(path)
        except OSError as exc:
            print(f"无法删除 {path}：{exc}", file=sys.stderr)
            success = False

    for directory in (_state_dir(),):
        try:
            directory.rmdir()
        except (FileNotFoundError, OSError):
            pass
    return success


def _unstall(args: argparse.Namespace) -> int:
    uv_path = shutil.which("uv")
    if uv_path is None:
        print("无法卸载：未找到 uv。", file=sys.stderr)
        return 1

    stop_result = _stop(args)
    if stop_result != 0:
        return stop_result
    if not _uninstall_playwright():
        return 1
    if not _remove_installation_files():
        return 1

    try:
        result = subprocess.run(
            [uv_path, "tool", "uninstall", "voxpull"],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"无法卸载全局 vox 命令：{exc}", file=sys.stderr)
        return 1

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        suffix = f"：{detail}" if detail else ""
        print(f"无法卸载全局 vox 命令{suffix}", file=sys.stderr)
        return 1

    print("VoxPull 已卸载。源码、用户数据和共享的 Homebrew 依赖已保留。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vox",
        description="VoxPull 本地服务管理命令",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    start_parser = subparsers.add_parser("start", help="启动项目并在后台运行")
    start_parser.set_defaults(handler=_start)

    status_parser = subparsers.add_parser("status", help="查看项目运行状态")
    status_parser.set_defaults(handler=_status)

    stop_parser = subparsers.add_parser("stop", help="停止后台项目")
    stop_parser.set_defaults(handler=_stop)

    restart_parser = subparsers.add_parser("restart", help="停止后重新启动项目")
    restart_parser.set_defaults(handler=_restart)

    port_parser = subparsers.add_parser("port", help="显示当前项目运行端口")
    port_parser.set_defaults(handler=_port)

    unstall_parser = subparsers.add_parser("unstall", help="卸载项目安装的文件")
    unstall_parser.set_defaults(handler=_unstall)

    help_parser = subparsers.add_parser("help", help="展示可用命令")
    help_parser.set_defaults(handler=lambda _args: parser.print_help() or 0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 0
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
