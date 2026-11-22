"""Local media responses and a bridge for already-running app sessions.

New application instances serve /api/jobs/{id}/video directly. The temporary
bridge lets the current older instance retain its in-memory task results. It
exits automatically when that instance stops and is not needed after restart.
Explicit file deletion is restricted to the local app origin and recorded files.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from voxpull.infrastructure.publication import PublicationLookup, publication_timestamp
from voxpull.infrastructure.job_files import DeleteJobFilesRequest, delete_job_files
from voxpull.domain.errors import VoxPullError


def video_file_response(path: Path) -> FileResponse:
    if path.suffix.lower() != ".mp4" or not path.is_file():
        raise HTTPException(status_code=404, detail="视频文件已移动或不存在")
    response = FileResponse(
        path, media_type="video/mp4", filename=path.name, content_disposition_type="inline"
    )
    response.headers["Cache-Control"] = "private, max-age=3600"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def create_preview_bridge(main_port: int, parent_pid: int, auth_backend_port: int | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{main_port}", timeout=10, trust_env=False
        ) as client:
            app.state.client = client

            async def watch_parent():
                while True:
                    await asyncio.sleep(2)
                    try:
                        os.kill(parent_pid, 0)
                    except ProcessLookupError:
                        app.state.server.should_exit = True
                        return

            monitor = asyncio.create_task(watch_parent())
            try:
                yield
            finally:
                monitor.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await monitor
                if hasattr(app.state, "auth_browser"):
                    await app.state.auth_browser.close()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[f"http://127.0.0.1:{main_port}", f"http://localhost:{main_port}"],
        allow_methods=["GET", "HEAD", "POST"],
        allow_headers=["Content-Type"],
    )
    app.state.publication_lookup = PublicationLookup()

    @app.exception_handler(VoxPullError)
    async def auth_error(_request: Request, exc: VoxPullError):
        return JSONResponse(status_code=502 if exc.code == "browser_failed" else 409,
                            content={"code": exc.code, "message": exc.message, "retryable": exc.retryable})

    def auth_browser():
        if not hasattr(app.state, "auth_browser"):
            from voxpull.config import Settings
            from voxpull.infrastructure.browser import PlaywrightBrowser

            settings = Settings.from_env()
            app.state.auth_browser = PlaywrightBrowser(
                settings.browser_profile_dir, settings.storage_state_path,
                settings.browser_timeout_seconds,
            )
        return app.state.auth_browser

    async def shared_auth(action: str, request: Request | None = None):
        try:
            path = f"http://127.0.0.1:{auth_backend_port}/api/auth/douyin/{action}"
            if request is None or request.method == "GET":
                response = await app.state.client.get(path)
            else:
                response = await app.state.client.post(path, content=await request.body(),
                    headers={"Origin": f"http://127.0.0.1:{main_port}", "Content-Type": "application/json"})
            return JSONResponse(response.json(), status_code=response.status_code)
        except httpx.HTTPError as exc:
            raise HTTPException(503, "共享登录后台暂不可用，请稍后重试") from exc

    @app.get("/api/auth/douyin/capabilities")
    async def auth_capabilities():
        if auth_backend_port:
            return await shared_auth("capabilities")
        return {"version": 2, "auto_save": True, "chrome_import": sys.platform == "darwin"}

    @app.get("/api/auth/douyin/status")
    async def auth_status():
        if auth_backend_port:
            return await shared_auth("status")
        return {"status": await auth_browser().auth_status()}

    @app.post("/api/auth/douyin/{action}")
    async def auth_action(action: str, request: Request):
        if request.headers.get("origin") not in {
            f"http://127.0.0.1:{main_port}", f"http://localhost:{main_port}",
        }:
            raise HTTPException(403, "仅允许从本地应用更新登录信息")
        if auth_backend_port:
            if action not in {"start", "complete", "import-chrome"}:
                raise HTTPException(404, "登录操作不存在")
            return await shared_auth(action, request)
        methods = {"start": "start_auth", "complete": "complete_auth", "import-chrome": "import_chrome_cookies"}
        if action not in methods:
            raise HTTPException(404, "登录操作不存在")
        return {"status": await getattr(auth_browser(), methods[action])()}

    @app.post("/api/jobs/files/delete")
    async def delete_files(payload: DeleteJobFilesRequest, request: Request):
        if request.headers.get("origin") not in {
            f"http://127.0.0.1:{main_port}", f"http://localhost:{main_port}",
        }:
            raise HTTPException(403, "仅允许从本地应用删除文件")

        async def lookup(job_id: str):
            try:
                response = await app.state.client.get(f"/api/jobs/{quote(job_id, safe='')}")
            except httpx.HTTPError as exc:
                raise HTTPException(503, "本地任务服务暂不可用，未删除文件") from exc
            if response.status_code != 200:
                try:
                    response = await app.state.client.get(
                        f"http://127.0.0.1:{main_port + 2}/api/jobs/{quote(job_id, safe='')}"
                    )
                except httpx.HTTPError as exc:
                    raise HTTPException(404, "任务不存在，未删除文件") from exc
                if response.status_code != 200:
                    raise HTTPException(404, "任务不存在，未删除文件")
            return response.json()

        return await delete_job_files(payload, lookup)

    @app.get("/api/jobs/{job_id}/publication")
    async def publication(job_id: str):
        try:
            response = await app.state.client.get(f"/api/jobs/{quote(job_id, safe='')}")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="本地任务服务暂不可用") from exc
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="任务不存在")
        media = (response.json().get("result") or {}).get("media") or {}
        stamp = publication_timestamp(media.get("published_at"))
        if stamp is None:
            stamp = await app.state.publication_lookup.get(str(media.get("id") or ""))
        return {"published_at": stamp}

    @app.api_route("/api/jobs/{job_id}/video", methods=["GET", "HEAD"])
    async def preview(job_id: str):
        try:
            response = await app.state.client.get(f"/api/jobs/{quote(job_id, safe='')}")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="本地任务服务暂不可用") from exc
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="任务不存在")
        result = response.json().get("result") or {}
        media = result.get("media") or {}
        if media.get("kind") != "video" or media.get("saved") is not True:
            raise HTTPException(status_code=404, detail="此任务没有保留可预览的视频")
        return video_file_response(Path(media["absolute_path"]))

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-port", type=int, required=True)
    parser.add_argument("--parent-pid", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    app = create_preview_bridge(args.main_port, args.parent_pid, auth_backend_port=args.main_port + 2)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=args.port, log_level="info"))
    app.state.server = server
    server.run()


if __name__ == "__main__":
    main()
