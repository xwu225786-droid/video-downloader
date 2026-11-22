"""Host-side companion for Finder, directory selection and explicit Chrome import.

No TCP listener and no Docker socket access. Requests arrive through a private
bind-mounted directory owned by the current user, and paths are allowlisted.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from voxpull.infrastructure.file_lock import lock_file

from voxpull.infrastructure.directory_picker import NativeDirectoryPicker
from voxpull.infrastructure.path_opener import NativePathOpener
from voxpull.infrastructure.verification_hook import VerificationHook


def checked_path(value: str, roots: list[Path]) -> Path:
    original = Path(value).expanduser()
    if not original.is_absolute():
        raise ValueError("本机目录必须使用绝对路径")
    path = original.resolve()
    if not any(path.is_relative_to(root) for root in roots):
        raise ValueError("该目录未挂载到 Docker；请选择素材目录内的位置，或先添加对应挂载")
    return path


def dispatch(action: str, payload: dict, roots: list[Path], auth_path: Path) -> dict:
    if action == "ping":
        return {"platform": __import__("sys").platform}
    if action == "recognize-slider":
        from voxpull.infrastructure.slider_recognition import recognize
        return recognize(payload)
    if action == "reveal":
        path = checked_path(payload["path"], roots)
        NativePathOpener()._reveal_sync(path)
        return {"opened": True}
    if action == "choose":
        initial = checked_path(payload["path"], roots)
        selected = NativeDirectoryPicker()._choose_sync(initial)
        return {"path": str(checked_path(str(selected), roots)) if selected else None}
    if action == "import-chrome":
        from voxpull.infrastructure.chrome_auth import import_chrome_douyin_state
        import_chrome_douyin_state(auth_path)
        return {"status": "saved"}
    raise ValueError("不支持的本机操作")


def process_request(path: Path, roots: list[Path], auth_path: Path) -> None:
    working = path.with_name(path.name.replace(".request.json", ".working.json"))
    response = path.with_name(path.name.replace(".request.json", ".response.json"))
    try:
        path.rename(working)
    except FileNotFoundError:
        return
    try:
        data = json.loads(working.read_text(encoding="utf-8"))
        expires = float(data["expires_at"])
        if not time.time() < expires <= time.time() + 180:
            raise ValueError("本机请求已过期")
        result = {"ok": True, "result": dispatch(data["action"], data.get("payload", {}), roots, auth_path)}
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    finally:
        working.unlink(missing_ok=True)
    temporary = response.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--media-root", type=Path, action="append", default=[])
    parser.add_argument("--verification-script", type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    # Host actions run without the container's bridge environment to avoid recursion.
    os.environ.pop("VOXPULL_HOST_BRIDGE_DIR", None)
    roots = list(dict.fromkeys([args.data_dir.resolve(), *(p.resolve() for p in args.media_root)]))
    hook = (VerificationHook(args.data_dir / "task-records", args.verification_script.resolve(),
                             directory.parent / "verification-hook.log")
            if args.verification_script else None)
    stopped = False
    def stop(*_):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with (directory / ".owner.lock").open("a") as handle, ThreadPoolExecutor(max_workers=3) as pool:
        lock_file(handle, blocking=False)
        last_health = 0
        last_hook_poll = 0
        scheduled = set()
        try:
            while not stopped:
                if time.monotonic() - last_health > 2:
                    (directory / "health.json").write_text(json.dumps({
                        "protocol": 1, "pid": os.getpid(),
                        "slider_operation": 1,
                        "verification_script": str(args.verification_script.resolve())
                        if args.verification_script else None,
                    }))
                    last_health = time.monotonic()
                if hook and time.monotonic() - last_hook_poll > 2:
                    hook.poll(pool)
                    last_hook_poll = time.monotonic()
                for path in directory.glob("*.request.json"):
                    if not path.is_symlink() and path not in scheduled:
                        scheduled.add(path)
                        task = pool.submit(process_request, path, roots, args.data_dir / "auth/storage-state.json")
                        task.add_done_callback(lambda _, p=path: scheduled.discard(p))
                for pattern in ("*.response.json", "*.working.json"):
                    for path in directory.glob(pattern):
                        try:
                            if time.time() - path.stat().st_mtime > 300:
                                path.unlink(missing_ok=True)
                        except FileNotFoundError:
                            pass
                time.sleep(.15)
        finally:
            (directory / "health.json").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
