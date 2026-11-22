"""Isolate the official SDK's blocking WebSocket loop from FastAPI's event loop."""
from __future__ import annotations

import argparse
import asyncio
import threading
import time
from pathlib import Path

from voxpull.infrastructure.cookies import save_storage_state
from voxpull.infrastructure.feishu_api import FeishuAPI
from voxpull.infrastructure.feishu_store import FeishuConfigStore, FeishuInbox


def normalize_event(data, app_id, bot_id):
    event = data.event
    message, sender = event.message, event.sender
    if sender.sender_type != "user" or message.message_type not in {"text", "post"}:
        return None
    if len(message.content or "") > 100_000:
        return None
    return {"app_id": app_id, "bot_id": bot_id, "message_id": message.message_id,
            "chat_id": message.chat_id, "chat_type": message.chat_type,
            "sender_id": sender.sender_id.open_id, "message_type": message.message_type,
            "content": message.content,
            "mentions": [getattr(item.id, "open_id", None) for item in message.mentions or []]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    config = FeishuConfigStore(args.config).load()
    if not config.enabled:
        return
    store = FeishuInbox(args.directory)
    status_path = args.directory / "listener.json"
    save_storage_state(status_path, {"status": "connecting", "updated_at": time.time()})

    async def identity():
        api = FeishuAPI(config)
        try:
            return await api.bot_info()
        finally:
            await api.close()

    try:
        bot = asyncio.run(identity())
        bot_id = bot.get("open_id")
        if not bot_id:
            raise RuntimeError("Missing bot identity")
        # Import after identity(): the pinned SDK owns its own synchronous loop.
        import lark_oapi as lark

        def receive(data):
            event = normalize_event(data, config.app_id, bot_id)
            if event:
                store.receive(event)

        dispatcher = lark.EventDispatcherHandler.builder("", "").register_p2_im_message_receive_v1(receive).build()
        client = lark.ws.Client(config.app_id, config.app_secret, event_handler=dispatcher,
                                log_level=lark.LogLevel.ERROR)

        def heartbeat():
            while True:
                # SDK 1.7.5 keeps _conn only for its active socket; a process
                # being alive alone must not be reported as a working connection.
                connection = getattr(client, "_conn", None)
                connected = connection is not None and not getattr(connection, "closed", False)
                save_storage_state(status_path, {"status": "connected" if connected else "connecting",
                                                 "updated_at": time.time()})
                time.sleep(2)

        threading.Thread(target=heartbeat, daemon=True).start()
        client.start()
    except Exception:
        save_storage_state(status_path, {"status": "error", "updated_at": time.time(),
                                         "message": "飞书连接失败，请检查凭证、机器人能力和网络"})
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
