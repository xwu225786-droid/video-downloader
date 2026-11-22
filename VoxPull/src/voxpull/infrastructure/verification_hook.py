"""Watch persisted jobs on the Mac and call a fixed, user-editable Python script."""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from concurrent.futures import Executor, Future
from pathlib import Path


logger = logging.getLogger(__name__)
WAITING_STATES = {"opening", "verification_required", "window_closed", "refresh_required"}


class VerificationHook:
    def __init__(self, records: Path, script: Path, log_path: Path):
        self.records = records
        self.script = script
        self.log_path = log_path
        self._notified: set[str] = set()
        self._future: Future | None = None

    def poll(self, executor: Executor) -> None:
        waiting = {}
        unreadable = set()
        for path in self.records.glob("job-*.json"):
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
                state = job.get("metadata", {}).get("auth_status")
                if (job.get("status") == "running"
                        and job.get("stage") == "acquiring_cookie" and state in WAITING_STATES):
                    waiting[path.stem] = job
            except (OSError, ValueError, AttributeError, TypeError):
                # A partial write must not reset deduplication for an active wait.
                unreadable.add(path.stem)
        self._notified.intersection_update(waiting.keys() | unreadable)
        if self._future is not None and not self._future.done():
            return
        for key, job in waiting.items():
            if key in self._notified:
                continue
            self._notified.add(key)
            self._future = executor.submit(self._run, job)
            break

    def _run(self, job: dict) -> None:
        state = job["metadata"]["auth_status"]
        content = job.get("content", "")
        url = re.search(r"https?://[^\s<>]+", content)
        event = {"event": "manual_verification_required", "job_id": job["id"],
                 "auth_status": state, "message": job.get("message", ""),
                 "content": content, "url": url.group(0) if url else ""}
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as log:
                log.write(f"\n启动你好.py job_id={job['id']} state={state}\n")
                log.flush()
                subprocess.run(
                    [sys.executable, str(self.script)], cwd=self.script.parent,
                    input=json.dumps(event, ensure_ascii=False), text=True,
                    stdout=log, stderr=subprocess.STDOUT, timeout=270, check=True,
                )
        except Exception:
            logger.exception("人工验证脚本运行失败，原任务继续等待人工验证")
