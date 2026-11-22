from __future__ import annotations

import base64
import hashlib


def safe_media_id(value: str) -> str:
    cleaned = "".join(ch for ch in value if ch.isalnum() or ch in "_-")
    return cleaned[:128] or "video"


def compact_media_id(value: str) -> str:
    digest = hashlib.sha256(safe_media_id(value).encode("utf-8")).digest()
    return base64.b32encode(digest).decode("ascii").lower()[:10]
