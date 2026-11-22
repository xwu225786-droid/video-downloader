import json
from concurrent.futures import ThreadPoolExecutor

from voxpull.infrastructure.verification_hook import VerificationHook


def write_job(root, ident="one", state="verification_required", status="running"):
    path = root / f"job-{ident}.json"
    path.write_text(json.dumps({
        "id": ident, "status": status, "stage": "acquiring_cookie",
        "content": "测试 https://www.douyin.com/video/123", "message": "请完成验证",
        "metadata": {"auth_status": state},
    }))
    return path


def poll(hook, pool):
    hook.poll(pool)
    if hook._future:
        hook._future.result(timeout=5)


def test_real_script_receives_event_once_and_retry_can_trigger_again(tmp_path):
    script = tmp_path / "你好.py"
    output = tmp_path / "events.jsonl"
    script.write_text(
        "import json, sys\nfrom pathlib import Path\n"
        "with Path('events.jsonl').open('a') as f:\n"
        " f.write(json.dumps(json.load(sys.stdin)) + '\\n')\n"
    )
    job = write_job(tmp_path)
    hook = VerificationHook(tmp_path, script, tmp_path / "hook.log")
    with ThreadPoolExecutor() as pool:
        poll(hook, pool)
        poll(hook, pool)
        job.write_text("{")  # Simulate a file being written by the application.
        poll(hook, pool)
        write_job(tmp_path, state="window_closed")
        poll(hook, pool)
        assert len(output.read_text().splitlines()) == 1
        write_job(tmp_path, status="paused")
        poll(hook, pool)
        write_job(tmp_path)
        poll(hook, pool)
    events = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(events) == 2
    assert events[0] == {
        "event": "manual_verification_required", "job_id": "one",
        "auth_status": "verification_required", "message": "请完成验证",
        "content": "测试 https://www.douyin.com/video/123", "url": "https://www.douyin.com/video/123",
    }


def test_only_active_human_waits_trigger_and_script_errors_do_not_escape(tmp_path):
    script = tmp_path / "你好.py"
    script.write_text("raise RuntimeError('example failure')")
    hook = VerificationHook(tmp_path, script, tmp_path / "hook.log")
    write_job(tmp_path, "waiting", state="waiting_browser")
    write_job(tmp_path, "failed", status="failed")
    write_job(tmp_path, "ready", state="checking")
    (tmp_path / "job-corrupt.json").write_text("{")
    with ThreadPoolExecutor() as pool:
        poll(hook, pool)
        assert hook._future is None
        write_job(tmp_path, "login", state="opening")
        poll(hook, pool)
        poll(hook, pool)
    log = (tmp_path / "hook.log").read_text()
    assert log.count("启动你好.py") == 1
    assert "example failure" in log
