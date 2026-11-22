import asyncio
import json
from pathlib import Path

import httpx
import pytest

from voxpull.domain.errors import DownloadFailedError
from voxpull.domain.models import ImageAssetMetadata, MediaKind, MediaMetadata
from voxpull.infrastructure.downloader import (
    YtDlpDownloader,
    _image_extension,
    _metadata_from_xiaohongshu_note,
    _xiaohongshu_mobile_options,
    _xiaohongshu_note_from_initial_state,
    _xiaohongshu_original_image_urls,
    _metadata_from_xiaohongshu_video,
    _normalize_xiaohongshu_url,
    _is_xiaohongshu_url,
)


@pytest.mark.parametrize("outcome", ["video", "no_media", "blocked_media", "external_redirect"])
async def test_douyin_public_fallback_uses_only_available_anonymous_copy(tmp_path, monkeypatch, outcome):
    import voxpull.infrastructure.downloader as module

    share = "https://www.iesdouyin.com/share/video/123/"
    video = "https://www.iesdouyin.com/aweme/v1/playwm/?video_id=fixture"
    mp4 = b"\x00\x00\x00\x18ftypmp42fixture"
    requests = []

    def respond(request):
        requests.append(str(request.url))
        assert "cookie" not in request.headers
        if str(request.url) == share:
            detail = {"aweme_id": "123", "video": {"play_addr": {"url_list": [video]}}}
            payload = {} if outcome == "no_media" else {"items": [detail]}
            return httpx.Response(200, text=f"<script>window._ROUTER_DATA = {json.dumps(payload)}</script>",
                                  headers={"set-cookie": "session=fixture"})
        assert str(request.url) == video
        if outcome == "external_redirect":
            return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})
        return httpx.Response(403 if outcome == "blocked_media" else 200, content=mp4)

    client = httpx.AsyncClient
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kw: client(transport=httpx.MockTransport(respond), **kw))
    evidence = await YtDlpDownloader(2).download_public_douyin_share(
        "https://www.douyin.com/video/123", tmp_path / "cookies.txt",
    )
    if outcome == "video":
        assert evidence.downloaded_video.read_bytes() == mp4
        assert evidence.media.source_urls == (video,)
    else:
        assert evidence is None and not list(tmp_path.iterdir())
    assert requests == ([share] if outcome == "no_media" else [share, video])


@pytest.mark.parametrize("host", ["xhslink.cn", "xhslink.com", "www.xhslink.cn", "www.xiaohongshu.com"])
def test_xiaohongshu_short_link_domains_are_recognized(host):
    assert _is_xiaohongshu_url(f"https://{host}/o/example")
    assert not _is_xiaohongshu_url(f"https://{host}.unrelated.example/o/example")


def test_login_redirect_restores_note_without_changing_signature():
    from urllib.parse import urlencode
    original = "https://www.xiaohongshu.com/discovery/item/abcdef?xsec_token=a%2Bb%3D&xsec_source=share"
    wrapped = "https://www.xiaohongshu.com/login?" + urlencode({"redirectPath": original})
    assert _normalize_xiaohongshu_url(wrapped) == original
    with pytest.raises(DownloadFailedError):
        _normalize_xiaohongshu_url("https://www.xiaohongshu.com/login?" + urlencode({"redirectPath": "https://unrelated.example/video"}))


def test_xiaohongshu_public_video_uses_stream_fields_and_prefers_h264_https():
    metadata = _metadata_from_xiaohongshu_video({
        "type": "video", "title": "公开作品", "video": {"media": {"stream": {
            "h265": [{"masterUrl": "https://sns-video.xhscdn.com/hevc.mp4", "height": 1080}],
            "h264": [{"masterUrl": "http://sns-video.xhscdn.com/h264.mp4?sign=a%2Bb",
                      "duration": 208562, "height": 720,
                      "backupUrls": ["https://unrelated.example/ignore.mp4"]}],
        }}},
    }, "abcdef")
    assert metadata is not None
    assert metadata.kind is MediaKind.VIDEO and metadata.duration == 208.562
    assert metadata.source_urls == (
        "https://sns-video.xhscdn.com/h264.mp4?sign=a%2Bb",
        "http://sns-video.xhscdn.com/h264.mp4?sign=a%2Bb",
        "https://sns-video.xhscdn.com/hevc.mp4",
    )


def test_direct_xiaohongshu_download_keeps_its_own_referer(tmp_path):
    from types import SimpleNamespace
    seen = []

    class YDL:
        def __init__(self, options): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def process_ie_result(self, info, download):
            seen.append(info)
            return info
        def prepare_filename(self, info): return str(tmp_path / "video.mp4")

    metadata = MediaMetadata("id", "title", source_urls=("https://sns-video.xhscdn.com/test.mp4",))
    options = YtDlpDownloader._base_options(tmp_path / "cookies.txt", "test-agent",
                                           "https://www.xiaohongshu.com/explore/abcdef")
    YtDlpDownloader._download_direct_video(SimpleNamespace(YoutubeDL=YDL), options,
                                            metadata, "test-agent", tmp_path, "video")
    assert seen[0]["http_headers"]["Referer"] == "https://www.xiaohongshu.com/"
    assert seen[0]["protocol"] == "https"


def test_direct_video_tries_ranked_high_quality_and_only_falls_back_on_error(tmp_path):
    from types import SimpleNamespace
    seen = []
    class YDL:
        def __init__(self, options): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def process_ie_result(self, info, download):
            seen.append(info["url"])
            if "high" in info["url"]:
                raise DownloadFailedError("resource unavailable")
            return info
        def prepare_filename(self, info): return str(tmp_path / "video.mp4")
    metadata = MediaMetadata("123", "video", source_urls=(
        "https://cdn.example/high-primary.mp4", "https://cdn.example/high-backup.mp4",
        "https://cdn.example/lower.mp4", "https://cdn.example/lowest.mp4",
    ))
    YtDlpDownloader._download_direct_video(SimpleNamespace(YoutubeDL=YDL), {}, metadata,
                                           "test-agent", tmp_path, "video")
    assert seen == list(metadata.source_urls[:3])


def test_direct_download_does_not_send_douyin_referer(tmp_path: Path) -> None:
    options = YtDlpDownloader._base_options(
        tmp_path / "cookies.txt",
        "test-agent",
        "https://vod.dkhs.com/path/video.mp4",
    )

    assert options["http_headers"] == {"User-Agent": "test-agent"}


def test_douyin_download_keeps_douyin_referer(tmp_path: Path) -> None:
    options = YtDlpDownloader._base_options(
        tmp_path / "cookies.txt",
        "test-agent",
        "https://www.douyin.com/video/123",
    )

    assert options["http_headers"]["Referer"] == "https://www.douyin.com/"


def test_xiaohongshu_note_preserves_images_and_live_motion() -> None:
    metadata = _metadata_from_xiaohongshu_note(
        {
            "type": "normal",
            "title": "地铁looooook",
            "desc": "第一段正文\n第二段 #日常[话题]#",
            "imageList": [
                {
                    "width": 1440,
                    "height": 1920,
                    "urlDefault": "https://sns.example/one.webp",
                    "urlPre": "https://sns.example/one-preview.webp",
                    "livePhoto": True,
                    "stream": {
                        "h264": [
                            {
                                "masterUrl": "https://sns-video.example/one.mp4",
                                "backupUrls": [
                                    "https://sns-video.example/one-backup.mp4"
                                ],
                            }
                        ]
                    },
                },
                {
                    "urlDefault": "https://sns.example/two.jpg",
                    "livePhoto": False,
                    "stream": {"h264": []},
                },
            ],
        },
        "6a48e5fd0000000021023784",
    )

    assert metadata is not None
    assert metadata.kind is MediaKind.IMAGES
    assert metadata.title == "地铁looooook"
    assert metadata.description == "第一段正文\n第二段 #日常[话题]#"
    assert metadata.image_source_policy == "xiaohongshu-original-png-v3"
    assert len(metadata.images) == 2
    assert metadata.images[0].motion_urls == (
        "https://sns-video.example/one.mp4",
        "https://sns-video.example/one-backup.mp4",
    )
    assert not metadata.images[1].is_live


def test_xiaohongshu_mobile_state_finds_note_data() -> None:
    note = {
        "noteId": "69a6b5b0000000000d009fe8",
        "title": "天鹅湖 🦢",
        "imageList": [{"url": "https://sns.example/one.webp"}],
    }

    assert (
        _xiaohongshu_note_from_initial_state(
            {"noteData": {"data": {"noteData": note}}},
            "69a6b5b0000000000d009fe8",
        )
        is note
    )


def test_xiaohongshu_mobile_state_rejects_a_different_note() -> None:
    assert (
        _xiaohongshu_note_from_initial_state(
            {
                "noteData": {
                    "data": {
                        "noteData": {
                            "noteId": "another-note",
                            "imageList": [{"url": "https://sns.example/one.webp"}],
                        }
                    }
                }
            },
            "expected-note",
        )
        is None
    )


def test_xiaohongshu_video_is_not_misclassified_as_an_image_post() -> None:
    assert (
        _metadata_from_xiaohongshu_note(
            {
                "noteId": "video-note",
                "noteType": "video",
                "imageList": [{"url": "https://sns.example/thumbnail.webp"}],
            },
            "video-note",
        )
        is None
    )


def test_xiaohongshu_original_images_exclude_watermarked_renders() -> None:
    metadata = _metadata_from_xiaohongshu_note(
        {
            "title": "原图测试",
            "imageList": [
                {
                    "fileId": "notes_pre_post/1040-original",
                    "url": "https://sns-webpic-qc.xhscdn.com/rendered!h5_1080jpg",
                }
            ],
        },
        "original-gallery",
    )

    assert metadata is not None
    assert metadata.images[0].source_urls == (
        "https://sns-img-qc.xhscdn.com/notes_pre_post/1040-original",
        "https://sns-img-bd.xhscdn.com/notes_pre_post/1040-original",
    )


def test_xiaohongshu_original_image_ids_are_safely_encoded() -> None:
    assert _xiaohongshu_original_image_urls(
        {"fileId": "notes_pre_post/image id", "traceId": "../unsafe"}
    ) == (
        "https://sns-img-qc.xhscdn.com/notes_pre_post/image%20id",
        "https://sns-img-bd.xhscdn.com/notes_pre_post/image%20id",
    )


def test_xiaohongshu_image_probe_uses_mobile_share_user_agent(tmp_path: Path) -> None:
    options = YtDlpDownloader._base_options(
        tmp_path / "cookies.txt",
        "desktop-agent",
        "https://www.xiaohongshu.com/discovery/item/test",
    )
    request_options = _xiaohongshu_mobile_options(options)

    assert request_options["http_headers"]["User-Agent"].startswith("Mozilla/5.0 (iPhone;")
    assert request_options["http_headers"]["Referer"] == "https://www.xiaohongshu.com/"
    assert options["http_headers"]["User-Agent"] == "desktop-agent"


def test_image_extension_prefers_verified_content() -> None:
    assert _image_extension("image/webp", "https://cdn.example/no-ext", b"data") == "webp"
    assert (
        _image_extension(
            "application/octet-stream",
            "https://cdn.example/no-ext",
            b"\xff\xd8\xff\xe0",
        )
        == "jpg"
    )
    assert _image_extension("text/html", "https://cdn.example/page", b"<html>") is None


async def test_heif_download_is_converted_to_lossless_png(tmp_path: Path) -> None:
    from PIL import Image, ImageOps
    from pillow_heif import register_heif_opener

    register_heif_opener()
    source = tmp_path / "source.heic"
    Image.new("RGB", (37, 23), (18, 52, 86)).save(source, format="HEIF", quality=100)
    heif_bytes = source.read_bytes()
    with Image.open(source) as original:
        expected_pixels = ImageOps.exif_transpose(original).convert("RGB").tobytes()

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/octet-stream"},
            content=heif_bytes,
        )

    metadata = MediaMetadata(
        id="heif-gallery",
        title="HEIF 图集",
        kind=MediaKind.IMAGES,
        images=(
            ImageAssetMetadata(index=1, source_urls=("https://cdn.example/original",)),
        ),
    )
    downloader = YtDlpDownloader(timeout=5, image_transport=httpx.MockTransport(handler))

    gallery = await downloader.download_images(
        "https://www.xiaohongshu.com/discovery/item/heif-gallery",
        metadata,
        tmp_path / "cookies.txt",
        "test-agent",
        tmp_path / "work",
        lambda _value, _message: None,
    )

    destination = gallery / "001.png"
    with Image.open(destination) as converted:
        assert converted.format == "PNG"
        assert converted.size == (37, 23)
        assert converted.convert("RGB").tobytes() == expected_pixels
    assert not (gallery / "001.heic").exists()
    manifest = json.loads((gallery / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["assets"][0]["image"] == "001.png"


async def test_image_client_supports_socks_proxy_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALL_PROXY", "socks5h://127.0.0.1:7890")
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)

    async with httpx.AsyncClient():
        pass


async def test_image_downloads_share_the_configured_concurrency_limit(tmp_path: Path) -> None:
    active = 0
    maximum_active = 0
    three_started = asyncio.Event()
    release = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active, maximum_active
        active += 1
        maximum_active = max(maximum_active, active)
        if active == 3:
            three_started.set()
        try:
            await release.wait()
        finally:
            active -= 1
        return httpx.Response(200, headers={"Content-Type": "image/webp"}, content=b"image")

    metadata = MediaMetadata(
        id="gallery-concurrency",
        title="并发图集",
        kind=MediaKind.IMAGES,
        images=tuple(
            ImageAssetMetadata(index=index, source_urls=(f"https://cdn.example/{index}",))
            for index in range(1, 6)
        ),
    )
    progress: list[int] = []
    downloader = YtDlpDownloader(
        timeout=5,
        image_concurrency=3,
        image_transport=httpx.MockTransport(handler),
    )

    task = asyncio.create_task(
        downloader.download_images(
            "https://www.douyin.com/note/gallery-concurrency",
            metadata,
            tmp_path / "cookies.txt",
            "test-agent",
            tmp_path,
            lambda value, _message: progress.append(value),
        )
    )
    try:
        await asyncio.wait_for(three_started.wait(), timeout=1)
        assert maximum_active == 3
    finally:
        release.set()
    gallery = await task

    assert maximum_active == 3
    assert progress == sorted(progress)
    assert progress[-1] == 100
    assert sorted(path.name for path in gallery.glob("*.webp")) == [
        "001.webp",
        "002.webp",
        "003.webp",
        "004.webp",
        "005.webp",
    ]
    manifest = json.loads((gallery / "manifest.json").read_text(encoding="utf-8"))
    assert [asset["index"] for asset in manifest["assets"]] == [1, 2, 3, 4, 5]


async def test_image_download_falls_back_and_saves_live_motion(tmp_path: Path) -> None:
    requested_paths: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        assert request.headers["referer"] == "https://www.xiaohongshu.com/"
        if request.url.path == "/unavailable":
            return httpx.Response(503)
        if request.url.path == "/image":
            return httpx.Response(
                200,
                headers={"Content-Type": "image/jpeg"},
                content=b"\xff\xd8\xffimage",
            )
        return httpx.Response(
            200,
            headers={"Content-Type": "video/mp4"},
            content=b"\x00\x00\x00\x18ftypisom-live",
        )

    metadata = MediaMetadata(
        id="gallery-live",
        title="Live 图集",
        kind=MediaKind.IMAGES,
        images=(
            ImageAssetMetadata(
                index=1,
                source_urls=(
                    "https://cdn.example/unavailable",
                    "https://cdn.example/image",
                ),
                motion_urls=("https://cdn.example/motion",),
            ),
        ),
    )
    downloader = YtDlpDownloader(
        timeout=5,
        image_concurrency=2,
        image_transport=httpx.MockTransport(handler),
    )

    gallery = await downloader.download_images(
        "https://www.xiaohongshu.com/discovery/item/gallery-live",
        metadata,
        tmp_path / "cookies.txt",
        "test-agent",
        tmp_path,
        lambda _value, _message: None,
    )

    assert requested_paths.index("/unavailable") < requested_paths.index("/image")
    assert (gallery / "001.jpg").read_bytes() == b"\xff\xd8\xffimage"
    assert (gallery / "001.live.mp4").read_bytes() == b"\x00\x00\x00\x18ftypisom-live"
    manifest = json.loads((gallery / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["assets"][0]["motion"] == "001.live.mp4"


async def test_failed_image_stream_removes_partial_file(tmp_path: Path) -> None:
    class BrokenStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"first chunk"
            raise httpx.ReadError("stream interrupted")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "image/webp"},
            stream=BrokenStream(),
        )

    metadata = MediaMetadata(
        id="gallery-failed",
        title="失败图集",
        kind=MediaKind.IMAGES,
        images=(ImageAssetMetadata(index=1, source_urls=("https://cdn.example/broken",)),),
    )
    downloader = YtDlpDownloader(
        timeout=5,
        image_transport=httpx.MockTransport(handler),
    )

    with pytest.raises(DownloadFailedError):
        await downloader.download_images(
            "https://www.douyin.com/note/gallery-failed",
            metadata,
            tmp_path / "cookies.txt",
            "test-agent",
            tmp_path,
            lambda _value, _message: None,
        )

    gallery = tmp_path / "images"
    assert not (gallery / ".001.part").exists()
    assert not (gallery / "manifest.json").exists()
