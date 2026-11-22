from __future__ import annotations

import logging
import os
from pathlib import Path

import uvicorn

from voxpull.config import Settings
from voxpull.logging_config import configure_logging


def main() -> None:
    configured_log_path = os.getenv("VOXPULL_LOG_PATH")
    configure_logging(Path(configured_log_path) if configured_log_path else None)
    settings = Settings.from_env()
    logging.getLogger(__name__).info(
        "event=server_process_starting host=%s port=%s file_logging=%s",
        settings.host,
        settings.port,
        bool(configured_log_path),
    )
    uvicorn.run(
        "voxpull.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
