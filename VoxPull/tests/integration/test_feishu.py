import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from test_api import make_settings
from voxpull.app import create_app
from voxpull.application.feishu_service import FeishuService, admitted, message_links
from voxpull.application.job_service import InMemoryJobRepository, JobService
from voxpull.domain.models import (
    JobResult, JobStage, JobStatus, MediaInfo, MediaKind, Transcript,
)
from voxpull.infrastructure.feishu_api import FeishuAPI, FeishuApiError, MAX_FILE_BYTES
from voxpull.infrastructure.feishu_listener import normalize_event
from voxpull.infrastructure.feishu_store import FeishuConfig, FeishuConfigStore, FeishuInbox
from voxpull.infrastructure.storage import LocalStorage


def event(**changes):
    return {"app_id": "cli_test", "bot_id": "ou_bot", "message_id": "om_first",
            "chat_id": "oc_private", "chat_type": "p2p", "sender_id": "ou_user",
            "message_type": "text", "content": json.dumps({"text": "分享 https://v.douyin.com/test/"}),
            "mentions": [], **changes}


def config(**changes):
    return FeishuConfig(enabled=True, app_id="cli_test", app_secret="never-return-this",
                        allowed_users=["ou_user"], **changes)


class FakeAPI:
    def __init__(self):
        self.messages = []
        self.uploads = []
        self.fail_video_once = False

    async def send(self, chat, kind, content, uuid):
        if kind == "media" and self.fail_video_once:
            self.fail_video_once = False
            raise FeishuApiError("temporary failure")
        self.messages.append((chat, kind, content, uuid))
        return f"om_{len(self.messages)}"

    async def upload(self, path, **kwargs):
        self.uploads.append((path, kwargs))
        return f"key_{len(self.uploads)}"

    async def close(self):
        pass


def service(tmp_path):
    data = tmp_path / "data"
    storage = LocalStorage(data / "work", data / "videos", data / "images")
    jobs = JobService(InMemoryJobRepository(), object(), max_queue=20)
    jobs._accepting = True
    result = FeishuService(data, jobs, storage)
    result.config = config()
    result.api = FakeAPI()
    return result


def finish(service, ident, *, size=5, outside=False):
    root = service.storage.videos_root / "作品"
    root.mkdir(exist_ok=True)
    video = (service.directory.parent.parent / "private.txt") if outside else root / "视频.mp4"
    with video.open("wb") as f:
        f.truncate(size)
    cover = root / "封面.jpg"
    cover.write_bytes(b"cover")
    result = JobResult(MediaInfo("123", "作品标题", MediaKind.VIDEO, "视频.mp4", str(video), True,
                                duration=3, cover_path=str(cover)), Transcript("测试文案", (), "zh"))
    service.jobs.repository.update(ident, status=JobStatus.RUNNING)
    service.jobs.repository.update(ident, status=JobStatus.COMPLETED, stage=JobStage.COMPLETED, result=result)
    return video


def test_text_rich_links_and_exact_bot_mentions():
    e = event(content=json.dumps({"text": "https://example.com/a https://v.douyin.com/a/。 https://v.douyin.com/a/ https://douyin.com.evil.test/no"}))
    assert message_links(e) == ["https://v.douyin.com/a/"]
    e["content"] = json.dumps({"zh_cn": {"title": "分享", "content": [[{"tag": "a", "href": "https://xhslink.com/a", "text": "作品"}]]}})
    assert message_links(e) == ["https://xhslink.com/a"]
    cfg = config(allowed_chats=["oc_group"])
    assert admitted(event(), cfg)
    assert not admitted(event(sender_id="ou_other"), cfg)
    group = event(chat_type="group", chat_id="oc_group", mentions=["all", "ou_other"])
    assert not admitted(group, cfg)
    group["mentions"] = ["ou_bot"]
    assert admitted(group, cfg)
    assert not admitted({**group, "chat_id": "oc_other"}, cfg)
    assert not admitted(event(app_id="cli_other"), cfg)
    many = event(content=json.dumps({"text": " ".join(f"https://b23.tv/{i}" for i in range(11))}))
    with pytest.raises(ValueError, match="10"):
        message_links(many)


def test_listener_normalizes_only_user_text_messages():
    data = SimpleNamespace(event=SimpleNamespace(
        sender=SimpleNamespace(sender_type="user", sender_id=SimpleNamespace(open_id="ou_user")),
        message=SimpleNamespace(message_id="om_test", chat_id="oc_test", chat_type="group",
                                message_type="text", content='{"text":"hi"}',
                                mentions=[SimpleNamespace(id=SimpleNamespace(open_id="ou_bot"))])))
    normalized = normalize_event(data, "cli_test", "ou_bot")
    assert normalized["mentions"] == ["ou_bot"]
    data.event.sender.sender_type = "app"
    assert normalize_event(data, "cli_test", "ou_bot") is None


def test_official_sdk_dispatches_the_subscribed_event_to_durable_inbox(tmp_path):
    import lark_oapi as lark
    inbox = FeishuInbox(tmp_path / "inbox")

    def receive(data):
        inbox.receive(normalize_event(data, "cli_test", "ou_bot"))

    dispatcher = lark.EventDispatcherHandler.builder("", "").register_p2_im_message_receive_v1(receive).build()
    payload = {"schema": "2.0", "header": {"event_id": "event_test", "event_type": "im.message.receive_v1"},
               "event": {"sender": {"sender_type": "user", "sender_id": {"open_id": "ou_user"}},
                         "message": {"message_id": "om_test", "chat_id": "oc_private", "chat_type": "p2p",
                                     "message_type": "text", "content": event()["content"]}}}
    dispatcher.do_without_validation(json.dumps(payload).encode())
    dispatcher.do_without_validation(json.dumps(payload).encode())
    assert len(inbox.pending()) == 1
    assert inbox.pending()[0][1]["sender_id"] == "ou_user"


async def test_disabled_module_never_connects_and_private_config(tmp_path):
    s = service(tmp_path)
    s.api = None
    factory = AsyncMock()
    s.api_factory = factory
    await s.start()
    assert s.status()["status"] == "disabled" and s._task is None
    factory.assert_not_called()
    store = FeishuConfigStore(tmp_path / "config.json")
    store.save(config())
    assert store.path.stat().st_mode & 0o777 == 0o600
    assert "app_secret" not in store.load().public()
    assert store.load().public()["secret_saved"]


async def test_duplicate_messages_and_partial_delivery_resume_without_redownload(tmp_path):
    s = service(tmp_path)
    assert s.inbox().receive(event())
    assert not s.inbox().receive(event())
    await s.tick()
    ident = s.inbox().recent()[0]["job_ids"][0]
    assert s.jobs.get(ident).save_video and not s.jobs.get(ident).extract_txt
    finish(s, ident)
    s.api.fail_video_once = True
    await s.tick()
    assert s.inbox().recent()[0]["attempts"] == 1
    with s.inbox().connect() as db:
        key, raw = db.execute("SELECT id,data FROM messages").fetchone()
    data = json.loads(raw)
    s.inbox().save(key, data)
    # Recreate the coordinator with the same durable inbox and existing queue.
    restarted = FeishuService(s.directory.parent, s.jobs, s.storage)
    restarted.config, restarted.api = s.config, s.api
    await restarted.tick()
    assert restarted.inbox().recent()[0]["state"] == "done"
    assert s.jobs.queue.qsize() == 1
    kinds = [message[1] for message in s.api.messages]
    assert kinds == ["text", "text", "image", "media", "file"]
    assert len(s.api.uploads) == 3  # cover/video uploaded once despite failed send
    assert s.api.uploads[-1][0].name == "文案.txt"
    assert len({message[3] for message in s.api.messages}) == len(s.api.messages)


async def test_rejected_senders_do_not_create_jobs_or_replies(tmp_path):
    s = service(tmp_path)
    s.inbox().receive(event(sender_id="ou_unknown"))
    await s.tick()
    assert s.jobs.queue.qsize() == 0 and not s.api.messages
    assert s.inbox().recent()[0]["state"] == "ignored"


@pytest.mark.parametrize("outside", [False, True])
async def test_large_or_outside_files_are_not_uploaded_and_text_is_delivered(tmp_path, outside):
    s = service(tmp_path)
    s.inbox().receive(event())
    await s.tick()
    ident = s.inbox().recent()[0]["job_ids"][0]
    path = finish(s, ident, size=5 if outside else MAX_FILE_BYTES + 1, outside=outside)
    await s.tick()
    assert s.inbox().recent()[0]["state"] == "done"
    assert path.exists()
    assert all(uploaded != path for uploaded, _ in s.api.uploads)
    assert any(message[1] == "file" for message in s.api.messages)
    assert not any(message[1] == "media" for message in s.api.messages)


async def test_verification_notice_is_sent_once_and_deleted_job_is_not_recreated(tmp_path):
    s = service(tmp_path)
    s.inbox().receive(event())
    await s.tick()
    ident = s.inbox().recent()[0]["job_ids"][0]
    s.jobs.repository.update(ident, metadata={"auth_status": "verification_required"})
    await s.tick()
    await s.tick()
    assert len(s.api.messages) == 2
    del s.jobs.repository._jobs[ident]
    await s.tick()
    assert s.jobs.get(ident) is None and s.inbox().recent()[0]["state"] == "done"


async def test_delivery_retry_is_explicit_and_does_not_reset_sent_steps(tmp_path):
    inbox = FeishuInbox(tmp_path / "feishu")
    inbox.receive(event())
    key, data, _ = inbox.pending()[0]
    data["sent"] = {"accepted": "om_received"}
    inbox.save(key, data, state="delivery_failed", attempts=5, error="failed")
    assert not inbox.pending()
    assert inbox.retry(key)
    assert inbox.pending()[0][1]["sent"] == {"accepted": "om_received"}
    assert not inbox.retry("missing")


async def test_http_token_cache_upload_and_error_redaction(tmp_path):
    requests = []
    async def handler(request):
        requests.append(request)
        if request.url.path.endswith("/tenant_access_token/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "test-token", "expire": 7200})
        assert request.headers["Authorization"] == "Bearer test-token"
        if request.url.path.endswith("/files"):
            assert b'filename="' in await request.aread()
            return httpx.Response(200, json={"code": 0, "data": {"file_key": "file_uploaded"}})
        if request.url.path.endswith("/messages"):
            body = json.loads(request.content)
            assert body["uuid"] == "stable-uuid"
            return httpx.Response(200, json={"code": 0, "data": {"message_id": "om_sent"}})
        return httpx.Response(200, json={"code": 99991672, "msg": "never-return-this secret token test-token"})
    client = httpx.AsyncClient(base_url="https://open.feishu.cn/open-apis/", transport=httpx.MockTransport(handler))
    api = FeishuAPI(config(), client=client)
    path = tmp_path / "video.mp4"
    path.write_bytes(b"video")
    assert await api.upload(path, duration=3) == "file_uploaded"
    assert await api.send("oc_test", "text", {"text": "hi"}, "stable-uuid") == "om_sent"
    with pytest.raises(FeishuApiError) as caught:
        await api.bot_info()
    assert "test-token" not in str(caught.value) and "never-return" not in str(caught.value)
    assert sum(r.url.path.endswith("/tenant_access_token/internal") for r in requests) == 1
    await api.close()


async def test_api_masks_secrets_validates_config_origin_and_discovers_jobs(tmp_path):
    app = create_app(make_settings(tmp_path))
    s = app.state.container.feishu_service
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        base = "/api/integrations/feishu"
        assert (await client.get(base)).json()["status"] == "disabled"
        assert (await client.put(base + "/config", json={"enabled": True})).status_code == 422
        payload = {"app_id": "cli_test", "app_secret": "private-value", "allowed_users": ["ou_user"]}
        response = await client.put(base + "/config", json=payload)
        assert response.status_code == 200 and "private-value" not in response.text
        assert response.json()["config"]["secret_saved"]
        payload.pop("app_secret")
        assert (await client.put(base + "/config", json=payload)).status_code == 200
        assert s.config.app_secret == "private-value"
        assert (await client.put(base + "/config", json={**payload, "app_id": "cli_changed"})).status_code == 422
        assert (await client.delete(base + "/config", headers={"origin": "https://external.test"})).status_code == 403
        assert (await client.get(base + "/jobs")).json() == {"sources": []}
        await client.delete(base + "/config")
        assert not s.config.app_secret and not s.config.enabled
        assert (await client.post(base + "/test")).status_code == 422
