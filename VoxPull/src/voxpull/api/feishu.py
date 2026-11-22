from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, SecretStr

from voxpull.api.auth import check_origin
from voxpull.infrastructure.feishu_api import FeishuAPI, FeishuApiError
from voxpull.infrastructure.feishu_store import FeishuConfig


router = APIRouter(prefix="/api/integrations/feishu", tags=["feishu"])


class ConfigRequest(BaseModel):
    enabled: bool = False
    app_id: str = Field(default="", max_length=128)
    app_secret: SecretStr | None = None
    allowed_users: list[str] = Field(default_factory=list, max_length=100)
    allowed_chats: list[str] = Field(default_factory=list, max_length=100)
    group_require_mention: bool = True
    extract_txt: bool = False
    language: str = "zh"


@router.get("")
async def status(request: Request):
    return request.app.state.container.feishu_service.status()


@router.put("/config")
async def configure(payload: ConfigRequest, request: Request):
    check_origin(request)
    service = request.app.state.container.feishu_service
    values = payload.model_dump(exclude={"app_secret"})
    secret = payload.app_secret.get_secret_value().strip() if payload.app_secret else ""
    if values["app_id"].strip() != service.config.app_id and not secret:
        if values["enabled"] or service.config.app_secret:
            raise HTTPException(422, "更换App ID时请同时填写新的App Secret")
    values["app_secret"] = secret or service.config.app_secret
    try:
        config = FeishuConfig.model_validate(values)
    except ValueError as exc:
        # Pydantic error objects include input values: do not expose credentials.
        message = exc.errors()[0]["msg"] if hasattr(exc, "errors") else "配置格式无效"
        raise HTTPException(422, message.removeprefix("Value error, ")) from None
    await service.configure(config)
    return service.status()


@router.delete("/config")
async def clear(request: Request):
    check_origin(request)
    service = request.app.state.container.feishu_service
    await service.configure(FeishuConfig())
    return service.status()


@router.post("/test")
async def test_connection(request: Request):
    check_origin(request)
    config = request.app.state.container.feishu_service.config
    if not config.app_id or not config.app_secret:
        raise HTTPException(422, "请先保存App ID和App Secret")
    api = FeishuAPI(config)
    try:
        bot = await api.bot_info()
        if not bot.get("open_id"):
            raise HTTPException(502, "未取得机器人身份，请检查机器人能力是否开启")
        return {"ok": True, "bot_name": bot.get("app_name") or "飞书机器人"}
    except FeishuApiError as exc:
        raise HTTPException(502, str(exc)) from None
    finally:
        await api.close()


@router.get("/jobs")
async def job_sources(request: Request):
    return {"sources": request.app.state.container.feishu_service.sources()}


@router.post("/retry/{message_key}")
async def retry_delivery(message_key: str, request: Request):
    check_origin(request)
    service = request.app.state.container.feishu_service
    if not service.config.enabled:
        raise HTTPException(409, "请先启用飞书接入，再重试回传")
    if not service.inbox().retry(message_key):
        raise HTTPException(404, "未找到可重试的回传记录")
    return {"ok": True}
