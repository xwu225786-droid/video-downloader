"""Local message -> existing job queue -> resumable Feishu result delivery."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

from voxpull.application.pipeline import validate_url
from voxpull.domain.errors import QueueFullError, VoxPullError
from voxpull.domain.models import DOUYIN_PUBLIC_SHARE_POLICY, DOUYIN_GUEST_POLICY, JobStatus, MediaKind
from voxpull.infrastructure.feishu_api import FeishuAPI, MAX_FILE_BYTES, MAX_IMAGE_BYTES
from voxpull.infrastructure.feishu_store import FeishuConfig, FeishuConfigStore, FeishuInbox


logger = logging.getLogger(__name__)
_HOSTS = ("douyin.com", "iesdouyin.com", "xiaohongshu.com", "xhslink.com", "bilibili.com", "b23.tv")


def message_links(event):
    """Read text or rich-text hyperlinks; never submit arbitrary external URLs."""
    content = json.loads(event["content"])
    pieces = []

    def collect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"href", "text"} and isinstance(item, str):
                    pieces.append(item)
                elif isinstance(item, (dict, list)):
                    collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(content)
    urls = []
    for match in re.findall(r"https?://[^\s<>]+", "\n".join(pieces)):
        url = match.rstrip("。！？，,；;：:）)】]}>\"'")
        try:
            host = (urlparse(url).hostname or "").lower().rstrip(".")
            if any(host == allowed or host.endswith("." + allowed) for allowed in _HOSTS):
                url = validate_url(url)
                if url not in urls:
                    urls.append(url)
        except (VoxPullError, ValueError):
            continue
    if len(urls) > 10:
        raise ValueError("每条飞书消息最多提交10个链接，请分开发送")
    return urls


def admitted(event, config):
    if event.get("app_id") != config.app_id or not event.get("sender_id"):
        return False
    if event.get("chat_type") == "p2p":
        return event["sender_id"] in config.allowed_users
    if event.get("chat_type") != "group" or event.get("chat_id") not in config.allowed_chats:
        return False
    return not config.group_require_mention or bool(
        event.get("bot_id") and event["bot_id"] in event.get("mentions", []))


class FeishuService:
    def __init__(self, data_dir, jobs, storage, *, api_factory=FeishuAPI):
        self.config_store = FeishuConfigStore(data_dir / "auth/feishu-config.json")
        self.directory = data_dir / "feishu"
        self.jobs, self.storage = jobs, storage
        self.api_factory = api_factory
        self.config = FeishuConfig()
        self.store = None
        self.api = None
        self._task = None
        self._listener = None
        self._next_listener = 0
        self._lock = asyncio.Lock()
        self._error = ""

    def inbox(self):
        if self.store is None:
            self.store = FeishuInbox(self.directory)
        return self.store

    async def start(self):
        try:
            self.config = self.config_store.load()
        except (OSError, ValueError):
            self.config = FeishuConfig()
            self._error = "本地飞书配置读取失败，请重新保存配置"
        if self.config.enabled and self._task is None:
            self.api = self.api_factory(self.config)
            self._task = asyncio.create_task(self._run(), name="voxpull-feishu")

    async def stop(self):
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._listener and self._listener.returncode is None:
            self._listener.terminate()
            try:
                await asyncio.wait_for(self._listener.wait(), 5)
            except TimeoutError:
                self._listener.kill()
                await self._listener.wait()
        self._listener = None
        if self.api:
            await self.api.close()
            self.api = None

    async def configure(self, config):
        async with self._lock:
            await self.stop()
            self.config_store.save(config)
            self._error = ""
            self._next_listener = 0
            await self.start()

    def status(self):
        state = "disabled"
        if self.config.enabled:
            state = "connecting"
            path = self.directory / "listener.json"
            try:
                health = json.loads(path.read_text())
                if self._listener and self._listener.returncode is None and time.time() - health["updated_at"] < 15:
                    state = health["status"]
                elif self._listener and self._listener.returncode is not None:
                    state = "error"
            except (OSError, ValueError, KeyError):
                pass
        return {"config": self.config.public(), "status": state,
                "message": self._error or {"disabled": "未启用，配置后可接收飞书链接",
                "connecting": "正在连接飞书", "connected": "长连接已建立",
                "error": "连接失败，请检查凭证、机器人能力和网络"}.get(state, "状态未知"),
                "recent": self.inbox().recent() if self.directory.exists() else []}

    def sources(self):
        if not self.directory.exists():
            return []
        result = []
        for item in self.inbox().sources():
            job = self.jobs.get(item["job_id"])
            if job:
                result.append({"type": "single", "id": job.id, "submitted_at": job.created_at.isoformat(),
                               "payload": {"content": job.content, "language": job.language,
                                           "save_video": job.save_video, "extract_txt": job.extract_txt}})
        return result

    async def _run(self):
        while True:
            try:
                if (self._listener is None or self._listener.returncode is not None) and time.time() >= self._next_listener:
                    self.inbox()
                    (self.directory / "listener.json").unlink(missing_ok=True)
                    self._listener = await asyncio.create_subprocess_exec(
                        sys.executable, "-m", "voxpull.infrastructure.feishu_listener",
                        "--config", str(self.config_store.path), "--directory", str(self.directory),
                        stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL)
                    self._next_listener = time.time() + 30
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                self._error = "飞书后台暂时异常，将自动重试；本地任务不受影响"
                logger.warning("event=feishu_worker_retry")
            await asyncio.sleep(2)

    async def tick(self):
        if not self.config.enabled or self.api is None:
            return
        for key, data, attempts in self.inbox().pending():
            if not admitted(data, self.config):
                self.inbox().save(key, data, state="ignored")
                continue
            try:
                await self._process(key, data)
                self._error = ""
            except QueueFullError:
                self.inbox().save(key, data, next_at=time.time() + 5)
            except Exception:
                attempts += 1
                self.inbox().save(key, data, state="delivery_failed" if attempts >= 5 else "pending",
                                   attempts=attempts, next_at=time.time() + min(300, 5 * 2 ** attempts),
                                   error="处理或发送失败，可重试回传；已下载素材不会重复下载")

    def _checkpoint(self, key, data):
        self.inbox().save(key, data)

    async def _send(self, key, data, label, kind, content):
        sent = data.setdefault("sent", {})
        if label not in sent:
            message_id = await self.api.send(data["chat_id"], kind, content,
                uuid.uuid5(uuid.NAMESPACE_URL, key + ":" + label).hex)
            sent[label] = message_id
            self._checkpoint(key, data)

    async def _text(self, key, data, label, text):
        await self._send(key, data, label, "text", {"text": text[:12000]})

    async def _process(self, key, data):
        if "items" not in data:
            try:
                urls = message_links(data)
            except (ValueError, TypeError):
                await self._text(key, data, "invalid", "消息格式无效或链接过多，每条最多10个链接。")
                self.inbox().save(key, data, state="done")
                return
            if not urls:
                self.inbox().save(key, data, state="ignored")
                return
            data["extract_txt"] = self.config.extract_txt
            data["language"] = self.config.language
            data["items"] = [{"url": url, "job_id": uuid.uuid5(uuid.NAMESPACE_URL, key + ":" + url).hex}
                             for url in urls]
            self._checkpoint(key, data)
        for item in data["items"]:
            if self.jobs.get(item["job_id"]) is None:
                if item.get("submitted"):
                    continue
                # Persist the deterministic identity before submission: a restart
                # between queueing and checkpointing cannot create a second job.
                self.jobs.submit(item["url"], data["language"], True, data["extract_txt"],
                                 job_id=item["job_id"], metadata={"source": "feishu"})
            if not item.get("submitted"):
                item["submitted"] = True
                self._checkpoint(key, data)
        await self._text(key, data, "accepted", f"已收到 {len(data['items'])} 个链接，正在处理。")
        finished = True
        for item in data["items"]:
            job = self.jobs.get(item["job_id"])
            if job is None:
                await self._text(key, data, item["job_id"] + ":deleted", "任务已被删除，已停止回传。")
            elif job.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
                finished = False
                if job.metadata.get("auth_status") in {"opening", "verification_required", "window_closed"}:
                    await self._text(key, data, job.id + ":verification",
                                     "此任务需要登录或验证码。请在运行应用的Mac上打开“抖音登陆与验证窗口”完成，任务会继续。")
            elif job.status is JobStatus.PAUSED:
                await self._text(key, data, job.id + ":paused", "任务已在本机暂停，可在处理队列点击重试重新开始。")
            elif job.status is JobStatus.FAILED:
                await self._text(key, data, job.id + ":failed",
                                 f"处理失败：{job.error.message if job.error else job.message}\n原链接：{item['url']}\n可在本机处理队列单独重试。")
            elif job.result:
                await self._deliver(key, data, job)
            else:
                await self._text(key, data, job.id + ":missing", "任务结果已不可用，请在本机队列检查。")
        if finished:
            self.inbox().save(key, data, state="done")

    def _asset(self, raw):
        if not raw:
            return None
        path = Path(raw).resolve()
        roots = [self.storage.videos_root.resolve(), self.storage.images_root.resolve(),
                 (self.directory / "exports").resolve()]
        if path.is_file() and any(path.is_relative_to(root) for root in roots):
            return path
        return None

    async def _upload(self, key, data, label, path, *, image=False, duration=None):
        uploaded = data.setdefault("uploaded", {})
        if label not in uploaded:
            uploaded[label] = await self.api.upload(path, image=image, duration=duration)
            self._checkpoint(key, data)
        return uploaded[label]

    async def _deliver(self, key, data, job):
        media = job.result.media
        source = "\n视频来源：公开分享页水印版" if media.video_source_policy == DOUYIN_PUBLIC_SHARE_POLICY else ""
        if media.video_source_policy in {"douyin-guest-v1", DOUYIN_GUEST_POLICY}:
            source = "\n视频来源：访客公开资源"
        await self._text(key, data, job.id + ":title", f"{media.title}\n原链接：{job.content}{source}")
        cover = self._asset(media.cover_path)
        image_key = None
        if cover and 0 < cover.stat().st_size <= MAX_IMAGE_BYTES:
            image_key = await self._upload(key, data, job.id + ":cover", cover, image=True)
            await self._send(key, data, job.id + ":cover", "image", {"image_key": image_key})
        paths = [("video", self._asset(media.absolute_path), False)] if media.kind is MediaKind.VIDEO else [
            (f"image-{i}", self._asset(asset.absolute_path), True)
            for i, asset in enumerate(media.assets[:20]) if asset.kind.value == "image"]
        for name, path, image in paths:
            label = job.id + ":" + name
            if path is None:
                await self._text(key, data, label, "源文件已不存在或不在素材目录中，请在本机查看。")
                continue
            if not 0 < path.stat().st_size <= (MAX_IMAGE_BYTES if image else MAX_FILE_BYTES):
                await self._text(key, data, label, "文件超过飞书直接上传上限或文件为空；素材保留在本机，标题和文案会继续发送。")
                continue
            file_key = await self._upload(key, data, label, path, image=image, duration=media.duration)
            content = {"image_key": file_key} if image else {"file_key": file_key}
            if not image and image_key:
                content["image_key"] = image_key
            await self._send(key, data, label, "image" if image else "media", content)
        if media.kind is MediaKind.IMAGES and len(media.assets) > 20:
            await self._text(key, data, job.id + ":album-limit", "本次回传最多20张图片，完整素材已保存在本机。")
        text = job.result.transcript.text if job.result.transcript else media.description
        if text:
            exports = self.directory / "exports" / job.id
            exports.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = exports / "文案.txt"
            if not path.exists():
                path.write_text(text, encoding="utf-8")
                path.chmod(0o600)
            if path.stat().st_size <= MAX_FILE_BYTES:
                file_key = await self._upload(key, data, job.id + ":text", path)
                await self._send(key, data, job.id + ":text", "file", {"file_key": file_key})
