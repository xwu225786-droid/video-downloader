from __future__ import annotations

import os
import sys
from typing import Annotated

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from voxpull.api.schemas import AuthStatusResponse
from voxpull.application.pipeline import extract_douyin_url
from voxpull.infrastructure.host_bridge import bridge_configured
from voxpull.domain.models import JobStage, JobStatus

router = APIRouter(prefix="/api/auth/douyin", tags=["douyin-auth"])


class AuthStartRequest(BaseModel):
    job_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")] | None = None
    target_url: Annotated[str, Field(min_length=1, max_length=4096)] | None = None


class OperationRequest(BaseModel):
    job_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
    max_attempts: Annotated[int, Field(ge=1, le=3)] = 3


class CurrentOperationRequest(BaseModel):
    target_url: Annotated[str, Field(min_length=1, max_length=4096)]
    max_attempts: Annotated[int, Field(ge=1, le=3)] = 3


@router.post("/operate-current")
async def operate_idle_page(request: Request, payload: CurrentOperationRequest):
    """Explicitly test the existing idle page, without retrying or downloading a job."""
    check_origin(request)
    browser = request.app.state.container.browser
    target = extract_douyin_url(payload.target_url)
    status = await browser.auth_status()
    def same_idle_page():
        details = browser.auth_details()
        return (details.get("target_url") == target and not details.get("active_job")
                and details.get("waiting_jobs", 0) == 0)
    if status != "verification_required" or not same_idle_page():
        raise HTTPException(409, "当前页面已变化或有任务正在使用浏览器，未执行测试")
    return await browser.operate_current_slider(same_idle_page, allow_idle=True,
                                                max_attempts=payload.max_attempts)


@router.get("/operation-layout")
async def operation_layout(request: Request):
    check_origin(request)
    return await request.app.state.container.browser.inspect_slider_layout()


@router.post("/operate")
async def operate_current_page(request: Request, payload: OperationRequest):
    check_origin(request)
    container = request.app.state.container
    def waiting():
        job = container.job_service.get(payload.job_id)
        return (job is not None and job.status == JobStatus.RUNNING
                and job.stage == JobStage.ACQUIRING_COOKIE
                and job.metadata.get("auth_status") == "verification_required")
    if not waiting():
        raise HTTPException(409, "该任务当前没有等待滑块操作")
    return await container.browser.operate_current_slider(waiting, max_attempts=payload.max_attempts)


def check_origin(request: Request):
    origins = {str(request.base_url).rstrip("/")}
    legacy = getattr(request.app.state, "legacy_main_port", None)
    if legacy:
        origins.update({f"http://127.0.0.1:{legacy}", f"http://localhost:{legacy}"})
    if request.headers.get("origin") and request.headers["origin"] not in origins:
        raise HTTPException(403, "仅允许从本机应用操作登录或验证")


def response(request: Request, status: str):
    browser = request.app.state.container.browser
    details = browser.auth_details() if hasattr(browser, "auth_details") else {}
    return AuthStatusResponse(status=status, **details)


@router.get("/capabilities")
async def auth_capabilities():
    return {"version": 3, "auto_save": True, "shared_session": True,
            "current_page_operation": True,
            "manual_verification": True, "chrome_import": sys.platform == "darwin" or bridge_configured(),
            "browser_console_url": os.getenv("VOXPULL_BROWSER_CONSOLE_URL") or None}


@router.post("/import-chrome", response_model=AuthStatusResponse, response_model_exclude_defaults=True)
async def import_chrome(request: Request):
    check_origin(request)
    return response(request, await request.app.state.container.auth_service.import_chrome())


@router.post("/start", response_model=AuthStatusResponse, response_model_exclude_defaults=True)
async def start_auth(request: Request, payload: AuthStartRequest | None = None):
    check_origin(request)
    target = None
    if payload and payload.job_id and payload.target_url:
        raise HTTPException(422, "任务编号和作品直链只能提供一个")
    if payload and payload.target_url:
        target = extract_douyin_url(payload.target_url)
    if payload and payload.job_id:
        job = request.app.state.container.job_service.get(payload.job_id)
        if job is None:
            raise HTTPException(404, "任务不存在")
        target = extract_douyin_url(job.content)
    return response(request, await request.app.state.container.auth_service.start(target))


@router.post("/complete", response_model=AuthStatusResponse, response_model_exclude_defaults=True)
async def complete_auth(request: Request):
    check_origin(request)
    return response(request, await request.app.state.container.auth_service.complete())


@router.get("/status", response_model=AuthStatusResponse, response_model_exclude_defaults=True)
async def auth_status(request: Request):
    return response(request, await request.app.state.container.auth_service.status())
