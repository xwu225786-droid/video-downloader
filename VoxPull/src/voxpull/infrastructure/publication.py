"""Publication dates read from platform metadata, never inferred from task dates."""
from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime

import httpx


def publication_timestamp(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        stamp = float(value)
    except (ValueError, TypeError):
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return None
            stamp = parsed.timestamp()
        except ValueError:
            return None
    if stamp > 10**12:
        stamp /= 1000
    return int(stamp) if 946684800 <= stamp < 4102444800 else None


def publication_from_share_html(html: str, media_id: str) -> int | None:
    match = re.search(r"\bwindow\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>", html, re.S)
    if not match:
        return None
    try:
        payload = json.loads(match.group(1))
    except ValueError:
        return None

    def find(value):
        if isinstance(value, dict):
            actual = str(value.get("aweme_id") or value.get("awemeId") or value.get("id") or "")
            if actual == media_id:
                stamp = publication_timestamp(value.get("create_time") or value.get("createTime"))
                if stamp:
                    return stamp
            for nested in value.values():
                found = find(nested)
                if found:
                    return found
        elif isinstance(value, list):
            for nested in value:
                found = find(nested)
                if found:
                    return found
        return None

    return find(payload)


class PublicationLookup:
    def __init__(self) -> None:
        self.cache: dict[str, tuple[float, int | None]] = {}
        self.slots = asyncio.Semaphore(2)

    async def get(self, media_id: str) -> int | None:
        if not media_id.isdigit():
            return None
        cached = self.cache.get(media_id)
        if cached and time.monotonic() - cached[0] < (86400 if cached[1] else 300):
            return cached[1]
        async with self.slots:
            cached = self.cache.get(media_id)
            if cached and time.monotonic() - cached[0] < (86400 if cached[1] else 300):
                return cached[1]
            # Public metadata only; no video streams, login state or file writes.
            from voxpull.infrastructure.browser import _MOBILE_SHARE_USER_AGENT

            stamp = None
            try:
                async with httpx.AsyncClient(
                    timeout=12, follow_redirects=True, trust_env=False,
                    headers={"User-Agent": _MOBILE_SHARE_USER_AGENT},
                ) as client:
                    response = await client.get(f"https://www.iesdouyin.com/share/video/{media_id}/")
                    if response.is_success:
                        stamp = publication_from_share_html(response.text, media_id)
            except httpx.HTTPError:
                pass
            self.cache[media_id] = (time.monotonic(), stamp)
            return stamp
