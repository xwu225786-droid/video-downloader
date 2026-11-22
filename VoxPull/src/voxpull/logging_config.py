from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


LOG_RETENTION_DAYS = 3
LOG_ROLLOVER_TIME = time(0, 0)
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


logger = logging.getLogger(__name__)


def find_expired_log_files(
    log_path: Path,
    *,
    retention_days: int = LOG_RETENTION_DAYS,
    today: date | None = None,
) -> list[Path]:
    cutoff = (today or date.today()) - timedelta(days=retention_days)
    prefix = f"{log_path.name}."
    expired: list[Path] = []
    if not log_path.parent.is_dir():
        return expired
    for candidate in log_path.parent.iterdir():
        if not candidate.is_file() or not candidate.name.startswith(prefix):
            continue
        try:
            archive_date = date.fromisoformat(candidate.name.removeprefix(prefix))
        except ValueError:
            continue
        if archive_date <= cutoff:
            expired.append(candidate)
    return sorted(expired)


class DailyRetentionFileHandler(TimedRotatingFileHandler):
    def getFilesToDelete(self) -> list[str]:  # noqa: N802 - stdlib API name
        return [
            str(path)
            for path in find_expired_log_files(
                Path(self.baseFilename),
                retention_days=self.backupCount,
            )
        ]


def build_daily_file_handler(log_path: Path) -> DailyRetentionFileHandler:
    log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not log_path.exists():
        log_path.touch(mode=0o600)
    log_path.chmod(0o600)
    for expired_log in find_expired_log_files(log_path):
        expired_log.unlink()
    handler = DailyRetentionFileHandler(
        log_path,
        when="midnight",
        interval=1,
        backupCount=LOG_RETENTION_DAYS,
        encoding="utf-8",
        delay=True,
        atTime=LOG_ROLLOVER_TIME,
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    return handler


def configure_logging(log_path: Path | None = None) -> None:
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.close()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)

    if log_path is None:
        handler: logging.Handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    else:
        handler = build_daily_file_handler(log_path)
    root_logger.addHandler(handler)

    # Uvicorn's default format omits timestamps. Let all of its loggers use the
    # same root handler so application, access, and server messages stay uniform.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True


def file_logging_enabled() -> bool:
    return any(
        isinstance(handler, DailyRetentionFileHandler)
        for handler in logging.getLogger().handlers
    )


def seconds_until_next_rollover(now: datetime | None = None) -> float:
    current = now or datetime.now().astimezone()
    next_date = current.date() + timedelta(days=1)
    next_rollover = datetime.combine(next_date, LOG_ROLLOVER_TIME, tzinfo=current.tzinfo)
    return max(0.0, (next_rollover - current).total_seconds())


async def run_log_retention_scheduler() -> None:
    while True:
        await asyncio.sleep(seconds_until_next_rollover())
        # Emitting a record at midnight makes TimedRotatingFileHandler perform
        # the rollover immediately, including deletion of backups over 3 days.
        logger.info("event=log_retention_cleanup retention_days=%s", LOG_RETENTION_DAYS)
