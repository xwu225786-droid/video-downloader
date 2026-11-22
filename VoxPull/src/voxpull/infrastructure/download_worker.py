"""Current-session worker for optional transcription, without restarting old jobs."""
from __future__ import annotations

import argparse
import asyncio
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from voxpull.infrastructure.storage import _load_media_root

from voxpull.app import create_app
from voxpull.config import Settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-pid", type=int, required=True)
    parser.add_argument("--main-port", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    os.environ["VOXPULL_PORT"] = str(args.port)
    app = create_app(Settings.from_env())
    app.state.legacy_main_port = args.main_port
    app.add_middleware(CORSMiddleware,
        allow_origins=[f"http://127.0.0.1:{args.main_port}", f"http://localhost:{args.main_port}"],
        allow_methods=["GET", "POST", "HEAD"], allow_headers=["Content-Type"])

    @app.middleware("http")
    async def sync_storage_choice(request, call_next):
        if request.method == "POST" and request.url.path in {"/api/jobs", "/api/batches"}:
            container = app.state.container
            root = _load_media_root(container.settings.storage_location_path)
            if root is not None and root != container.storage.media_root:
                container.storage.update_media_root(root)
        return await call_next(request)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        async with original(application):
            async def watch_parent():
                while True:
                    await asyncio.sleep(.5)
                    try:
                        os.kill(args.parent_pid, 0)
                    except ProcessLookupError:
                        server.should_exit = True
                        return
            monitor = asyncio.create_task(watch_parent())
            try:
                yield
            finally:
                monitor.cancel()
                await asyncio.gather(monitor, return_exceptions=True)
    app.router.lifespan_context = lifespan
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=args.port, log_level="info"))
    server.run()


if __name__ == "__main__":
    main()
