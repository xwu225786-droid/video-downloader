"""Exclusive, process-wide locks on POSIX and native Windows.

Lock files are separate from the JSON files replaced atomically by writers.
The handle must remain open until unlock/close; Windows locks byte zero, even
for an empty file (the CRT permits locking beyond EOF).
"""
from __future__ import annotations

import errno
import os
import time
from typing import IO

if os.name == "nt":
    import msvcrt
else:
    import fcntl


def lock_file(handle: IO, *, blocking: bool = True) -> None:
    if os.name != "nt":
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        return
    position = handle.tell()
    try:
        handle.seek(0)
        while True:
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if not blocking:
                    raise BlockingIOError(exc.errno, "File is already locked") from exc
                time.sleep(0.05)
    finally:
        handle.seek(position)


def unlock_file(handle: IO) -> None:
    if os.name != "nt":
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return
    position = handle.tell()
    try:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        handle.seek(position)
