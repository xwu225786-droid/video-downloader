import json
from datetime import UTC, datetime

import httpx
import pytest

from voxpull.infrastructure.browser import _metadata_from_aweme_detail
from voxpull.infrastructure.publication import (
    PublicationLookup, publication_from_share_html, publication_timestamp,
)


@pytest.mark.parametrize("value", [1735689600, "1735689600", 1735689600000, "2025-01-01T00:00:00Z"])
def test_publication_time_normalizes_platform_seconds_milliseconds_and_timezone(value):
    assert publication_timestamp(value) == int(datetime(2025, 1, 1, tzinfo=UTC).timestamp())


@pytest.mark.parametrize("value", [None, True, 0, "", "not a date", "2025-01-01", float("nan")])
def test_missing_or_unqualified_dates_are_not_inferred(value):
    assert publication_timestamp(value) is None


def test_share_publication_matches_requested_work_not_another_video():
    payload = {"items": [{"aweme_id": "other", "create_time": 1700000000},
                         {"aweme_id": "123", "create_time": 1735689600}]}
    html = f"<script>window._ROUTER_DATA={json.dumps(payload)}</script>"
    assert publication_from_share_html(html, "123") == 1735689600
    assert publication_from_share_html(html, "missing") is None
    assert publication_from_share_html("verification required", "123") is None


def test_browser_capture_keeps_platform_publication_timestamp():
    detail = {"aweme_id": "123", "desc": "原始发布标题", "create_time": 1735689600,
              "video": {"play_addr": {"url_list": ["https://example.test/video.mp4"]}}}
    metadata = _metadata_from_aweme_detail(detail)
    assert metadata.published_at == 1735689600


async def test_publication_lookup_caches_platform_response_without_video_download(monkeypatch):
    calls = []

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def get(self, url):
            calls.append(url)
            return httpx.Response(200, text='<script>window._ROUTER_DATA={"aweme_id":"123",'
                                           '"create_time":1735689600}</script>')

    monkeypatch.setattr("voxpull.infrastructure.publication.httpx.AsyncClient", Client)
    lookup = PublicationLookup()
    assert await lookup.get("123") == 1735689600
    assert await lookup.get("123") == 1735689600
    assert await lookup.get("not-a-douyin-id") is None
    assert calls == ["https://www.iesdouyin.com/share/video/123/"]
