#!/usr/bin/env python3
"""Local Docker lifecycle, private host companion, and reversible native cutover."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".local-tools/state"
DATA = ROOT / "VoxPull/data"
PYTHON = ROOT / "VoxPull/.venv/bin/python"
ENV_FILE = STATE / "docker.env"
REGISTRY = STATE / "docker-deployment.json"
BRIDGE = STATE / "docker-bridge"
VERIFICATION_SCRIPT = ROOT / "scripts/你好.py"
DOCKER = shutil.which("docker") or str(Path.home()/".docker/bin/docker")


def run(args, **kwargs):
    args = [str(a) for a in args]
    if args[0] == "docker":args[0] = DOCKER
    return subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def compose(*args):
    return run(["docker", "compose", "--env-file", ENV_FILE, "-f", ROOT / "compose.yaml", *args])


def prepare():
    STATE.mkdir(parents=True, exist_ok=True)
    BRIDGE.mkdir(exist_ok=True, mode=0o700)
    BRIDGE.chmod(0o700)
    values = {"VOXPULL_DATA_PATH": str(DATA), "VOXPULL_BRIDGE_PATH": str(BRIDGE),
              "VOXPULL_UID": str(os.getuid()), "VOXPULL_GID": str(os.getgid()),
              "VOXPULL_HTTP_PORT": "18765", "VOXPULL_CONSOLE_PORT": "6080"}
    ENV_FILE.write_text("\n".join(f"{key}={json.dumps(value,ensure_ascii=False)}" for key, value in values.items()) + "\n")
    ENV_FILE.chmod(0o600)
    archive = ROOT / "docker/vendor/whisper-source.tar"
    if not archive.is_file():
        archive.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "-C", ROOT / ".local-tools/whisper.cpp", "archive", "HEAD", "-o", archive])


def native_env():
    env = os.environ.copy()
    env.update(VOXPULL_STATE_DIR=str(STATE), VOXPULL_DATA_DIR=str(DATA), VOXPULL_HOST="127.0.0.1", VOXPULL_PORT="18765",
               PLAYWRIGHT_BROWSERS_PATH=str(ROOT/".local-tools/browsers"),
               VOXPULL_MODEL_PATH=str(ROOT/"VoxPull/models/ggml-medium-q5_0.bin"),
               VOXPULL_VAD_MODEL_PATH=str(ROOT/"VoxPull/models/ggml-silero-v6.2.0.bin"),
               VOXPULL_FFMPEG_BIN=str(ROOT/".local-tools/bin/ffmpeg"),
               VOXPULL_WHISPER_BIN=str(ROOT/".local-tools/whisper.cpp/build/bin/whisper-cli"))
    env.pop("VOXPULL_HOST_BRIDGE_DIR", None)
    env.pop("VOXPULL_BROWSER_PROFILE_DIR", None)
    return env


def assert_idle():
    for path in (DATA/"task-records").glob("job-*.json"):
        job = json.loads(path.read_text())
        if job["status"] in {"running", "queued"}:
            raise RuntimeError("仍有处理中的任务，请完成任务后再切换运行方式")


def healthy():
    try:
        with urllib.request.urlopen("http://127.0.0.1:18765/api/auth/douyin/capabilities", timeout=2) as response:
            return bool(json.load(response).get("browser_console_url"))
    except Exception:
        return False


def start_bridge():
    pid_path = STATE/"docker-host-bridge.json"
    if pid_path.exists():
        pid = json.loads(pid_path.read_text())["pid"]
        try:
            os.kill(pid, 0)
            health = BRIDGE/"health.json"
            if health.exists() and time.time()-health.stat().st_mtime < 15:
                bridge_health = json.loads(health.read_text())
                if (bridge_health.get("verification_script") == str(VERIFICATION_SCRIPT)
                        and bridge_health.get("slider_operation") == 1):
                    return
                stop_bridge()
        except ProcessLookupError:
            pass
    command = [str(PYTHON), "-m", "voxpull.infrastructure.host_bridge_server", "--directory", str(BRIDGE),
               "--data-dir", str(DATA), "--verification-script", str(VERIFICATION_SCRIPT)]
    location = DATA/"storage-location.json"
    if location.is_file():
        media_root = Path(json.loads(location.read_text())["media_root"]).resolve()
        if not media_root.is_relative_to(DATA):
            raise RuntimeError("素材根目录位于默认数据目录外，请先在compose.yaml加入对应绑定挂载")
    with (STATE/"docker-host-bridge.log").open("ab") as log:
        process = subprocess.Popen(command, cwd=ROOT/"VoxPull", env=native_env(), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    pid_path.write_text(json.dumps({"pid":process.pid}))
    for _ in range(50):
        if (BRIDGE/"health.json").exists():return
        time.sleep(.1)
    raise RuntimeError("本机桥接启动失败")


def stop_bridge():
    path = STATE/"docker-host-bridge.json"
    if path.is_file():
        pid = json.loads(path.read_text())["pid"]
        try:
            command = subprocess.check_output(["ps", "-p", str(pid), "-o", "command="], text=True)
            if "voxpull.infrastructure.host_bridge_server" in command:
                os.kill(pid,signal.SIGTERM)
                for _ in range(50):
                    try:os.kill(pid,0)
                    except ProcessLookupError:break
                    time.sleep(.1)
        except (ProcessLookupError,subprocess.CalledProcessError):pass
        path.unlink(missing_ok=True)


def backup():
    directory = STATE/"docker-backups"/datetime.now().strftime("%Y%m%d-%H%M%S")
    directory.mkdir(parents=True, mode=0o700)
    for folder in ["task-records", "auth"]:
        if (DATA/folder).is_dir():shutil.copytree(DATA/folder,directory/folder)
    for name in ["material-tags.json", "storage-location.json"]:
        if (DATA/name).is_file():shutil.copy2(DATA/name,directory/name)
    return directory


def start():
    prepare()
    start_bridge()
    if healthy():
        print("Docker 应用已在运行：http://127.0.0.1:18765/")
        return
    assert_idle()
    directory = backup()
    native_was_running = (STATE/"runtime.json").is_file()
    if native_was_running:
        run([PYTHON,"-m","voxpull.cli","stop"],env=native_env())
        # Session-specific helpers exit when their parent process stops.
        for _ in range(100):
            helpers=[]
            for name in ["download-worker.json","video-preview.json"]:
                path=STATE/name
                if path.exists():
                    try:os.kill(json.loads(path.read_text())["pid"],0);helpers.append(name)
                    except ProcessLookupError:pass
            if not helpers:break
            time.sleep(.1)
    try:
        compose("up","-d","--no-build","--wait","--wait-timeout","90")
        if not healthy():raise RuntimeError("Docker启动后验证入口未就绪")
    except Exception:
        compose("down")
        if native_was_running:run([PYTHON,"-m","voxpull.cli","start"],env=native_env())
        raise
    REGISTRY.write_text(json.dumps({"mode":"docker","backup":str(directory),"url":"http://127.0.0.1:18765/"},ensure_ascii=False,indent=2))
    print("Docker 应用已启动：http://127.0.0.1:18765/\n验证窗口：http://127.0.0.1:6080/vnc.html?autoconnect=1&resize=scale")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["prepare","build","start","stop","status","rollback"])
    action=parser.parse_args().action
    STATE.mkdir(parents=True,exist_ok=True)
    with (STATE/"docker-command.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if action=="prepare":prepare()
        elif action=="build":prepare();compose("build")
        elif action=="start":start()
        elif action=="status":prepare();compose("ps")
        elif action=="stop":
            assert_idle();prepare();compose("stop");stop_bridge()
        elif action=="rollback":
            assert_idle();prepare();compose("down");stop_bridge()
            state=json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
            saved=Path(state.get("backup",""))/"auth/storage-state.json"
            if saved.is_file():shutil.copy2(saved,DATA/"auth/storage-state.json")
            REGISTRY.write_text(json.dumps({"mode":"native"}))
            run([PYTHON,"-m","voxpull.cli","start"],env=native_env())


if __name__=="__main__":main()
