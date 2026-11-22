from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from voxpull.domain.errors import TaskTimeoutError


LineCallback = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


class ProcessRunner:
    def __init__(self) -> None:
        self._active: set[asyncio.subprocess.Process] = set()

    async def run(
        self,
        args: Sequence[str],
        *,
        timeout: float,
        on_stdout_line: LineCallback | None = None,
        on_stderr_line: LineCallback | None = None,
    ) -> ProcessResult:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **({"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
               if sys.platform == "win32" else {"start_new_session": True}),
        )
        self._active.add(process)
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

        async def consume(
            stream: asyncio.StreamReader | None,
            chunks: list[str],
            callback: LineCallback | None,
        ) -> None:
            if stream is None:
                return
            while line := await stream.readline():
                text = line.decode("utf-8", errors="replace")
                chunks.append(text)
                if callback:
                    callback(text.rstrip())

        stdout_task = asyncio.create_task(consume(process.stdout, stdout_chunks, on_stdout_line))
        stderr_task = asyncio.create_task(consume(process.stderr, stderr_chunks, on_stderr_line))
        try:
            async with asyncio.timeout(timeout):
                await process.wait()
                await asyncio.gather(stdout_task, stderr_task)
        except TimeoutError as exc:
            await self._terminate(process)
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            raise TaskTimeoutError(detail="Command timed out") from exc
        except asyncio.CancelledError:
            await self._terminate(process)
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            raise
        finally:
            self._active.discard(process)
        return ProcessResult(
            process.returncode or 0, "".join(stdout_chunks), "".join(stderr_chunks)
        )

    async def close(self) -> None:
        await asyncio.gather(*(self._terminate(process) for process in tuple(self._active)))

    @staticmethod
    async def _terminate(process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        if sys.platform == "win32":
            # Kill the owned process tree, including FFmpeg/Whisper descendants.
            # terminate() on Windows would kill only the immediate child.
            def terminate_tree() -> None:
                result = subprocess.run(
                    ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True, check=False, timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode and process.returncode is None:
                    with contextlib.suppress(ProcessLookupError):
                        process.kill()
            try:
                await asyncio.to_thread(terminate_tree)
            except (OSError, subprocess.SubprocessError):
                with contextlib.suppress(ProcessLookupError):
                    process.kill()
            await process.wait()
            return
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            async with asyncio.timeout(3):
                await process.wait()
                return
        except TimeoutError:
            pass
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        with contextlib.suppress(Exception):
            await process.wait()
