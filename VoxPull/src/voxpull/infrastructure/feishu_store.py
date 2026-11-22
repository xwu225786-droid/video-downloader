"""Private configuration and durable inbox/outbox checkpoints for the local bot."""
from __future__ import annotations

import json
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from voxpull.infrastructure.cookies import save_storage_state


class FeishuConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    app_id: str = Field(default="", max_length=128)
    app_secret: str = Field(default="", max_length=512, repr=False)
    allowed_users: list[str] = Field(default_factory=list, max_length=100)
    allowed_chats: list[str] = Field(default_factory=list, max_length=100)
    group_require_mention: bool = True
    extract_txt: bool = False
    language: str = "zh"

    @field_validator("app_id", "app_secret")
    @classmethod
    def trim(cls, value):
        return value.strip()

    @field_validator("allowed_users", "allowed_chats")
    @classmethod
    def ids(cls, values):
        values = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        if any(not re.fullmatch(r"[A-Za-z0-9_-]{3,128}", value) for value in values):
            raise ValueError("用户或群 ID 格式无效")
        return values

    @model_validator(mode="after")
    def validate_enabled(self):
        if self.language not in {"zh", "auto"}:
            raise ValueError("识别语言只支持中文或自动判断")
        if self.enabled and (not self.app_id or not self.app_secret):
            raise ValueError("启用前请填写 App ID 和 App Secret")
        return self

    def public(self):
        return {**self.model_dump(exclude={"app_secret"}),
                "secret_saved": bool(self.app_secret)}


class FeishuConfigStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> FeishuConfig:
        if not self.path.exists():
            return FeishuConfig()
        return FeishuConfig.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, config: FeishuConfig):
        save_storage_state(self.path, config.model_dump())


class FeishuInbox:
    """One listener inserts, one application worker processes; IDs deduplicate delivery."""
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        self.path = directory / "messages.sqlite3"
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY, data TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0, next_at REAL NOT NULL DEFAULT 0,
                error TEXT NOT NULL DEFAULT '', created REAL NOT NULL)""")
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=1)
        try:
            with db:
                yield db
        finally:
            db.close()

    def receive(self, event: dict) -> bool:
        key = f"{event['app_id']}:{event['message_id']}"
        with self.connect() as db:
            if db.execute("SELECT 1 FROM messages WHERE id=?", (key,)).fetchone():
                return False
            count = db.execute("SELECT count(*) FROM messages WHERE state='pending'").fetchone()[0]
            if count >= 1000:
                raise RuntimeError("飞书待处理消息已达上限")
            result = db.execute("INSERT OR IGNORE INTO messages(id,data,created) VALUES(?,?,?)",
                                (key, json.dumps(event, ensure_ascii=False), time.time()))
        return result.rowcount == 1

    def pending(self, limit=10):
        with self.connect() as db:
            rows = db.execute("SELECT id,data,attempts FROM messages WHERE state='pending' "
                              "AND next_at<=? ORDER BY created LIMIT ?", (time.time(), limit)).fetchall()
        return [(key, json.loads(data), attempts) for key, data, attempts in rows]

    def save(self, key, data, *, state="pending", attempts=0, next_at=0, error=""):
        with self.connect() as db:
            db.execute("UPDATE messages SET data=?,state=?,attempts=?,next_at=?,error=? WHERE id=?",
                       (json.dumps(data, ensure_ascii=False), state, attempts, next_at, error, key))

    def recent(self, limit=30):
        with self.connect() as db:
            rows = db.execute("SELECT id,data,state,attempts,error,created FROM messages "
                              "ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": key, "state": state, "attempts": attempts, "error": error,
                 "created_at": created, "chat_type": json.loads(data).get("chat_type"),
                 "sender_id": json.loads(data).get("sender_id"), "chat_id": json.loads(data).get("chat_id"),
                 "job_ids": [item["job_id"] for item in json.loads(data).get("items", [])]}
                for key, data, state, attempts, error, created in rows]

    def retry(self, key):
        with self.connect() as db:
            result = db.execute("UPDATE messages SET state='pending',attempts=0,next_at=0,error='' "
                                "WHERE id=? AND state='delivery_failed'", (key,))
        return result.rowcount == 1

    def sources(self):
        with self.connect() as db:
            rows = db.execute("SELECT data FROM messages ORDER BY created DESC").fetchall()
        return [item for (raw,) in rows for item in json.loads(raw).get("items", [])]
