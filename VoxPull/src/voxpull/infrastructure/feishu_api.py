"""Feishu OpenAPI; tokens and secrets never leave this transport in responses/errors."""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import httpx


MAX_FILE_BYTES = 30 * 1024 * 1024
MAX_IMAGE_BYTES = 10 * 1024 * 1024


class FeishuApiError(Exception):
    pass


class FeishuAPI:
    def __init__(self, config, *, client=None):
        self.config = config
        self.client = client or httpx.AsyncClient(
            base_url="https://open.feishu.cn/open-apis/", timeout=90, trust_env=False)
        self._token = ""
        self._expires = 0
        self._token_lock = asyncio.Lock()

    async def close(self):
        await self.client.aclose()

    async def _token_value(self):
        async with self._token_lock:
            if self._token and time.time() < self._expires:
                return self._token
            try:
                response = await self.client.post("auth/v3/tenant_access_token/internal", json={
                    "app_id": self.config.app_id, "app_secret": self.config.app_secret})
                data = response.json()
                if response.status_code != 200 or data.get("code") != 0 or not data.get("tenant_access_token"):
                    raise FeishuApiError("飞书凭证验证失败，请检查 App ID 和 App Secret")
                self._token = data["tenant_access_token"]
                self._expires = time.time() + max(0, int(data.get("expire", 7200)) - 120)
                return self._token
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                raise FeishuApiError("无法连接飞书，请检查网络后重试") from exc

    async def _request(self, method, path, **kwargs):
        try:
            response = await self.client.request(method, path, headers={
                "Authorization": f"Bearer {await self._token_value()}"}, **kwargs)
            data = response.json()
            if response.status_code != 200 or data.get("code") != 0:
                code = data.get("code", response.status_code)
                if code in {99991661, 99991663, 99991664, 99991668}:
                    self._token, self._expires = "", 0
                raise FeishuApiError(f"飞书接口请求失败（代码 {code}），请检查权限、文件限制或稍后重试")
            return data
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise FeishuApiError("飞书请求未完成，将保留任务并重试发送") from exc

    async def bot_info(self):
        data = await self._request("GET", "bot/v3/info")
        return data.get("bot") or data.get("data", {}).get("bot") or {}

    async def send(self, chat_id, kind, content, uuid):
        data = await self._request("POST", "im/v1/messages", params={"receive_id_type": "chat_id"},
                                   json={"receive_id": chat_id, "msg_type": kind,
                                         "content": json.dumps(content, ensure_ascii=False), "uuid": uuid})
        return data["data"]["message_id"]

    async def upload(self, path: Path, *, image=False, duration=None):
        size = path.stat().st_size
        if not 0 < size <= (MAX_IMAGE_BYTES if image else MAX_FILE_BYTES):
            raise FeishuApiError("文件为空或超过飞书上传大小限制")
        fields = {"image_type": "message"} if image else {
            "file_type": "mp4" if path.suffix.lower() == ".mp4" else "stream", "file_name": path.name}
        if duration is not None and not image:
            fields["duration"] = str(max(0, int(duration * 1000)))
        with path.open("rb") as stream:
            result = await self._request("POST", "im/v1/images" if image else "im/v1/files",
                                         data=fields, files={"image" if image else "file": (path.name, stream)})
        return result["data"]["image_key" if image else "file_key"]
