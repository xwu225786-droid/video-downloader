"""Real OS checks: locking, process trees, lifecycle and Unicode paths."""
from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from voxpull.domain.errors import TaskTimeoutError
from voxpull.infrastructure.file_lock import lock_file, unlock_file
from voxpull.infrastructure.material_folders import ensure_material_folder
from voxpull.infrastructure.processes import ProcessRunner


def child_env() -> dict[str, str]:
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[2] / 'src')
    env['PYTHONUTF8'] = '1'
    return env


def test_lock_excludes_another_process_and_releases_on_close(tmp_path):
    path = tmp_path / '中文 空格.lock'
    code = '''
import sys
from voxpull.infrastructure.file_lock import lock_file
with open(sys.argv[1], 'a') as handle:
    try:
        lock_file(handle, blocking=False)
    except BlockingIOError:
        sys.exit(3)
'''
    def contender():
        return subprocess.run([sys.executable, '-c', code, str(path)], env=child_env(),
                              capture_output=True, timeout=15)
    with path.open('a') as handle:
        lock_file(handle)
        result = contender()
        assert result.returncode == 3, result.stderr
        unlock_file(handle)
        result = contender()
        assert result.returncode == 0, result.stderr
        lock_file(handle)
    assert contender().returncode == 0


@pytest.mark.parametrize('name', ['CON', 'aux.txt', 'NUL', 'COM1', 'LPT9.mp4', 'COM¹', 'CONIN$', 'CONOUT$.txt', '中文 标题'])
def test_material_names_can_be_created_on_windows(tmp_path, name):
    folder = ensure_material_folder(tmp_path, name, name)
    (folder / '文案.txt').write_text('完整保留中文', encoding='utf-8')
    assert (folder / '文案.txt').read_text(encoding='utf-8') == '完整保留中文'
    assert ensure_material_folder(tmp_path, name, '新标题') == folder


async def test_process_runner_reports_timeout_and_decodes_unicode():
    runner = ProcessRunner()
    result = await runner.run([sys.executable, '-X', 'utf8', '-c', "print('字幕 ready')"], timeout=15)
    assert result.returncode == 0 and result.stdout.strip() == '字幕 ready'
    with pytest.raises(TaskTimeoutError):
        await runner.run([sys.executable, '-c', 'import time; time.sleep(60)'], timeout=.5)
    assert not runner._active


async def test_cancelling_process_stops_its_child(tmp_path):
    heartbeat = tmp_path / 'heartbeat.txt'
    child = "import pathlib,sys,time\np=pathlib.Path(sys.argv[1])\nwhile True:\n p.write_text(str(time.time()))\n time.sleep(.03)"
    parent = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]]); time.sleep(60)"
    runner = ProcessRunner()
    task = asyncio.create_task(runner.run([sys.executable, '-c', parent, child, str(heartbeat)], timeout=30))
    try:
        async with asyncio.timeout(15):
            while not heartbeat.exists():
                await asyncio.sleep(.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        value = heartbeat.read_text()
        await asyncio.sleep(.3)
        assert heartbeat.read_text() == value, 'A descendant remained alive after cancellation'
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await runner.close()


async def test_native_cli_start_status_restart_stop(tmp_path):
    # Isolate state/data and an unused port from the user's running application.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = child_env()
    env.update(VOXPULL_STATE_DIR=str(tmp_path / 'state'), VOXPULL_DATA_DIR=str(tmp_path / '中文 data'),
               VOXPULL_HOST='127.0.0.1', VOXPULL_PORT=str(port))
    def cli(action):
        return subprocess.run([sys.executable, '-m', 'voxpull.cli', action], env=env,
                              capture_output=True, encoding='utf-8', errors='replace', timeout=50)
    try:
        started = await asyncio.to_thread(cli, 'start')
        assert started.returncode == 0, started.stdout + started.stderr
        runtime_path = tmp_path / 'state' / 'runtime.json'
        initial = runtime_path.read_bytes()
        again = await asyncio.to_thread(cli, 'start')
        assert again.returncode == 0 and runtime_path.read_bytes() == initial
        status = await asyncio.to_thread(cli, 'port')
        assert status.returncode == 0 and status.stdout.strip() == str(port)
        async with httpx.AsyncClient(trust_env=False) as client:
            response = await client.get(f'http://127.0.0.1:{port}/')
        assert response.status_code == 200
        restarted = await asyncio.to_thread(cli, 'restart')
        assert restarted.returncode == 0, restarted.stdout + restarted.stderr
        assert runtime_path.read_bytes() != initial
    finally:
        stopped = await asyncio.to_thread(cli, 'stop')
    assert stopped.returncode == 0, stopped.stdout + stopped.stderr
    assert not (tmp_path / 'state' / 'runtime.json').exists()
