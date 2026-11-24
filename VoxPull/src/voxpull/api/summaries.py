from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Request, Response, status

from voxpull.api.schemas import (
    SummaryConfigRequest,
    SummaryConfigResponse,
    SummaryGenerateRequest,
    SummaryModelsRequest,
    SummaryModelsResponse,
    VideoSummaryResponse,
)
from voxpull.domain.errors import SummaryInvalidInputError
from voxpull.domain.models import SummaryStyle


router = APIRouter(prefix="/api", tags=["summaries"])


def _normalize_base_url(base_url: str) -> str:
    if len(base_url) > 256:
        raise SummaryInvalidInputError("总结服务配置长度无效")
    normalized = base_url.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SummaryInvalidInputError("接口地址必须以 http:// 或 https:// 开头")
    return normalized


def _validate_config_payload(payload: SummaryConfigRequest, *, configured: bool) -> str:
    if len(payload.api_key) > 1024 or len(payload.model) > 128:
        raise SummaryInvalidInputError("总结服务配置长度无效")
    normalized = _normalize_base_url(payload.base_url)
    if not payload.model.strip():
        raise SummaryInvalidInputError("模型名称不能为空")
    if not payload.api_key.strip() and not configured:
        raise SummaryInvalidInputError("API Key 不能为空")
    return normalized


@router.get("/summary/config", response_model=SummaryConfigResponse)
async def get_summary_config(request: Request) -> SummaryConfigResponse:
    provider_status = request.app.state.container.summary_service.status()
    return SummaryConfigResponse(
        configured=provider_status.configured,
        base_url=provider_status.base_url,
        model=provider_status.model,
    )


@router.put("/summary/config", response_model=SummaryConfigResponse)
async def put_summary_config(
    payload: SummaryConfigRequest,
    request: Request,
) -> SummaryConfigResponse:
    service = request.app.state.container.summary_service
    normalized_base = _validate_config_payload(payload, configured=service.status().configured)
    await service.configure(normalized_base, payload.api_key, payload.model)
    provider_status = service.status()
    return SummaryConfigResponse(
        configured=provider_status.configured,
        base_url=provider_status.base_url,
        model=provider_status.model,
    )


@router.delete("/summary/config", status_code=status.HTTP_204_NO_CONTENT)
async def delete_summary_config(request: Request) -> Response:
    await request.app.state.container.summary_service.clear_configuration()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/summary/models", response_model=SummaryModelsResponse)
async def list_summary_models(
    payload: SummaryModelsRequest,
    request: Request,
) -> SummaryModelsResponse:
    if len(payload.api_key) > 1024:
        raise SummaryInvalidInputError("总结服务配置长度无效")
    normalized_base = _normalize_base_url(payload.base_url)
    models = await request.app.state.container.summary_service.list_models(
        normalized_base, payload.api_key
    )
    return SummaryModelsResponse(models=models)


@router.post("/summary/test")
async def test_summary_connection(payload: SummaryConfigRequest, request: Request):
    service = request.app.state.container.summary_service
    normalized = _validate_config_payload(payload, configured=service.status().configured)
    return await service.test_connection(normalized, payload.api_key, payload.model)


@router.post("/jobs/{job_id}/summary", response_model=VideoSummaryResponse)
async def generate_summary(
    job_id: str,
    payload: SummaryGenerateRequest,
    request: Request,
) -> VideoSummaryResponse:
    try:
        style = SummaryStyle(payload.style)
    except ValueError as exc:
        raise SummaryInvalidInputError("不支持的总结风格") from exc
    service = request.app.state.container.summary_service
    summary = await service.summarize(job_id, payload.transcript_text, style)
    return VideoSummaryResponse.from_domain(summary, style, service.status().model)
