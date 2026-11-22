import sys
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from voxpull.logging_config import (
    LOG_RETENTION_DAYS,
    build_daily_file_handler,
    find_expired_log_files,
    seconds_until_next_rollover,
)


def test_daily_log_handler_adds_time_and_keeps_three_backups(tmp_path: Path) -> None:
    log_path = tmp_path / "server.log"
    handler = build_daily_file_handler(log_path)
    try:
        record = logging.LogRecord(
            name="voxpull.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="event=test_message",
            args=(),
            exc_info=None,
        )
        handler.handle(record)
        handler.flush()

        line = log_path.read_text(encoding="utf-8")
        assert re.match(
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} INFO voxpull\.test event=test_message\n$",
            line,
        )
        assert handler.when == "MIDNIGHT"
        assert handler.backupCount == LOG_RETENTION_DAYS == 3
        if sys.platform != "win32":
            assert log_path.stat().st_mode & 0o777 == 0o600
    finally:
        handler.close()


def test_daily_log_handler_selects_archives_at_least_three_days_old(tmp_path: Path) -> None:
    log_path = tmp_path / "server.log"
    today = date(2026, 7, 19)
    expired = tmp_path / "server.log.2026-07-16"
    retained = tmp_path / "server.log.2026-07-17"
    invalid = tmp_path / "server.log.not-a-date"
    for path in (expired, retained, invalid):
        path.touch()

    assert find_expired_log_files(log_path, today=today) == [expired]


def test_daily_log_handler_removes_expired_archives_during_startup(tmp_path: Path) -> None:
    log_path = tmp_path / "server.log"
    expired_date = date.today() - timedelta(days=LOG_RETENTION_DAYS)
    expired = tmp_path / f"server.log.{expired_date.isoformat()}"
    expired.touch()

    handler = build_daily_file_handler(log_path)
    try:
        assert not expired.exists()
    finally:
        handler.close()


def test_daily_log_handler_preserves_existing_log_modification_time(tmp_path: Path) -> None:
    log_path = tmp_path / "server.log"
    log_path.touch()
    old_timestamp = 1_700_000_000
    os.utime(log_path, (old_timestamp, old_timestamp))

    handler = build_daily_file_handler(log_path)
    try:
        assert log_path.stat().st_mtime == old_timestamp
    finally:
        handler.close()


def test_next_log_rollover_is_local_midnight() -> None:
    local_timezone = timezone(timedelta(hours=8))
    now = datetime(2026, 7, 19, 23, 59, 30, tzinfo=local_timezone)

    assert seconds_until_next_rollover(now) == 30
