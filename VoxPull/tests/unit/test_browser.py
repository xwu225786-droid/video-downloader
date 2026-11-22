import json

from voxpull.domain.models import MediaKind, MediaMetadata
from voxpull.infrastructure.browser import (
    _metadata_from_aweme_detail,
    _metadata_from_mobile_share_html,
    _metadata_from_react_flight_scripts,
    _select_douyin_metadata,
    _internal_playback_url,
)


def test_internal_playback_omits_share_download_and_explicit_watermark() -> None:
    assert _metadata_from_aweme_detail({
        "aweme_id": "123", "video": {"download_addr": {
            "url_list": ["https://v.example/shared.mp4"]
        }}
    }) is None
    metadata = _metadata_from_aweme_detail({
        "aweme_id": "123", "video": {
            "download_addr": {"url_list": ["https://v.example/shared.mp4"]},
            "play_addr": {"url_list": ["https://v.example/play?watermark=1"]},
            "bit_rate": [{"play_addr": {"url_list": ["https://v.example/internal.mp4"]}}],
        },
    })
    assert metadata is not None
    assert metadata.source_urls == ("https://v.example/internal.mp4",)


def test_only_known_playback_endpoint_is_normalized() -> None:
    assert _internal_playback_url(
        "https://www.iesdouyin.com/aweme/v1/playwm/?video_id=123"
    ) == "https://www.iesdouyin.com/aweme/v1/play/?video_id=123"
    signed_cdn = "https://v.example/signed/abc.mp4?signature=original"
    assert _internal_playback_url(signed_cdn) == signed_cdn
    assert _internal_playback_url("https://v.example/aweme/v1/playwm/?id=123") is None


def test_video_quality_prefers_resolution_then_bitrate_before_cdn():
    def address(url, width, height):
        return {"width": width, "height": height, "url_list": [url]}
    metadata = _metadata_from_aweme_detail({
        "aweme_id": "123", "video": {
            "width": 1080, "height": 1920,
            "play_addr_h264": address("https://cdn.example/default.mp4", 576, 1024),
            "bit_rate": [
                {"bit_rate": 1_800_000, "play_addr": address("https://cdn.example/540.mp4", 576, 1024)},
                {"bit_rate": 1_200_000, "play_addr": address("https://cdn.example/1080-small.mp4", 1080, 1920)},
                {"bit_rate": 2_600_000, "play_addr": address("https://www.douyin.com/play/1080", 1080, 1920)},
                {"bit_rate": 2_600_000, "play_addr": address("https://cdn.example/1080-best.mp4", 1080, 1920)},
                {"bit_rate": 4_000_000, "play_addr": address("https://cdn.example/720.mp4", 720, 1280)},
            ],
        },
    })
    assert metadata.source_urls == (
        "https://cdn.example/1080-best.mp4", "https://www.douyin.com/play/1080",
        "https://cdn.example/1080-small.mp4", "https://cdn.example/720.mp4",
        "https://cdn.example/540.mp4", "https://cdn.example/default.mp4",
    )
    assert (metadata.video_width, metadata.video_height, metadata.video_bitrate) == (1080, 1920, 2_600_000)


def test_unknown_default_address_does_not_inherit_original_1080_dimensions():
    metadata = _metadata_from_aweme_detail({"aweme_id": "123", "video": {
        "width": 1080, "height": 1920,
        "play_addr_h264": {"url_list": ["https://cdn.example/unknown.mp4"]},
        "bit_rate": [{"bit_rate": 2_000_000, "play_addr": {
            "width": 720, "height": 1280, "url_list": ["https://cdn.example/720.mp4"],
        }}],
    }})
    assert metadata.source_urls[0] == "https://cdn.example/720.mp4"
    assert (metadata.video_width, metadata.video_height) == (720, 1280)


def test_metadata_selection_prefers_resolution_over_count_of_duplicate_low_urls():
    low = MediaMetadata("123", "low", source_urls=("https://cdn.example/low",) * 10,
                        video_width=576, video_height=1024, video_bitrate=3_000_000)
    high = MediaMetadata("123", "high", source_urls=("https://cdn.example/high",),
                         video_width=1080, video_height=1920, video_bitrate=2_000_000)
    assert _select_douyin_metadata([low, high], expected_media_id="123") is high


def test_same_resolution_uses_bitrate_and_duplicate_addresses_are_removed():
    address = {"width": 1080, "height": 1920, "data_size": 3000,
               "url_list": ["https://cdn.example/best.mp4"] * 2}
    metadata = _metadata_from_aweme_detail({"aweme_id": "123", "video": {
        "duration": 1000, "play_addr_h264": address,
        "bit_rate": [{"bit_rate": 1000, "play_addr": {
            "width": 1080, "height": 1920, "url_list": ["https://cdn.example/low.mp4"],
        }}, {"bit_rate": 24000, "play_addr": address}],
    }})
    assert metadata.source_urls == ("https://cdn.example/best.mp4", "https://cdn.example/low.mp4")
    assert metadata.video_bitrate == 24000


def test_metadata_from_aweme_detail_prefers_direct_h264_urls() -> None:
    metadata = _metadata_from_aweme_detail(
        {
            "aweme_id": "7661543472545008932",
            "desc": "测试作品",
            "duration": 711692,
            "video": {
                "play_addr_h264": {
                    "url_list": [
                        "https://www.douyin.com/aweme/v1/play/?video_id=one",
                        "https://v26-web.douyinvod.com/video/one",
                    ]
                },
                "play_addr": {
                    "url_list": ["https://v26-web.douyinvod.com/video/one"]
                },
            },
        }
    )

    assert metadata is not None
    assert metadata.kind is MediaKind.VIDEO
    assert metadata.id == "7661543472545008932"
    assert metadata.title == "测试作品"
    assert metadata.duration == 711.692
    assert metadata.source_urls == (
        "https://v26-web.douyinvod.com/video/one",
        "https://www.douyin.com/aweme/v1/play/?video_id=one",
    )


def test_metadata_from_aweme_detail_rejects_unsafe_or_missing_media() -> None:
    assert _metadata_from_aweme_detail(None) is None
    assert (
        _metadata_from_aweme_detail(
            {
                "aweme_id": "123",
                "video": {"play_addr": {"url_list": ["http://127.0.0.1/video"]}},
            }
        )
        is None
    )


def test_metadata_from_aweme_detail_reads_images_and_live_motion() -> None:
    metadata = _metadata_from_aweme_detail(
        {
            "aweme_id": "7587447081268047268",
            "desc": "今天吃苹果了吗",
            "images": [
                {
                    "width": 1440,
                    "height": 1920,
                    "url_list": ["https://p.example/one.webp"],
                    "video": {
                        "play_addr": {
                            "url_list": ["https://v.example/one.mp4"]
                        }
                    },
                },
                {
                    "display_image": {
                        "url_list": ["https://p.example/two.jpg"]
                    }
                },
            ],
            "video": {
                "play_addr": {"url_list": ["https://v.example/background.mp4"]}
            },
        }
    )

    assert metadata is not None
    assert metadata.kind is MediaKind.IMAGES
    assert metadata.id == "7587447081268047268"
    assert len(metadata.images) == 2
    assert metadata.images[0].source_urls == ("https://p.example/one.webp",)
    assert metadata.images[0].motion_urls == ("https://v.example/one.mp4",)
    assert metadata.images[1].source_urls == ("https://p.example/two.jpg",)
    assert not metadata.images[1].is_live


def test_metadata_from_aweme_detail_prefers_clean_douyin_image_variants() -> None:
    clean_webp = (
        "https://p3-sign.douyinpic.com/source~tplv-dy-lqen-new:1440:1920:q80.webp"
    )
    clean_jpeg = (
        "https://p3-sign.douyinpic.com/source~tplv-dy-lqen-new%3A1440:1920:q80.jpeg"
    )
    water_webp = (
        "https://p3-sign.douyinpic.com/"
        "source~tplv-dy-lqen-new-water:1440:1920:account:q80.webp"
    )
    water_jpeg = (
        "https://p3-sign.douyinpic.com/"
        "source~tplv-dy-lqen-new-water:1440:1920:account:q80.jpeg"
    )
    ordinary_fallback = "https://p3-sign.douyinpic.com/source-preview.webp"
    owner_watermark = "https://p3-sign.douyinpic.com/owner-copy.webp"
    legacy_water = (
        "https://p3-sign.douyinpic.com/"
        "source~tplv-dy-water-v2:account:1080:1920.webp"
    )
    aweme_clean = (
        "https://p3-sign.douyinpic.com/"
        "source~tplv-dy-aweme-images:q75.webp"
    )

    metadata = _metadata_from_aweme_detail(
        {
            "aweme_id": "7594083117851200612",
            "images": [
                {
                    "downloadUrlList": [legacy_water, water_webp, water_jpeg],
                    "urlList": [aweme_clean, clean_webp, clean_jpeg],
                    "display_image": {"url_list": [ordinary_fallback]},
                    "owner_watermark_image": {"url_list": [owner_watermark]},
                }
            ],
        }
    )

    assert metadata is not None
    assert metadata.image_source_policy == "douyin-clean-live-v2"
    assert metadata.images[0].source_urls == (
        aweme_clean,
        clean_webp,
        clean_jpeg,
        ordinary_fallback,
    )


def test_metadata_from_aweme_detail_keeps_watermarked_image_only_without_clean_fallback() -> None:
    watermarked = (
        "https://p3-sign.douyinpic.com/"
        "source~tplv-dy-lqen-new-water:1080:1920:account:q80.webp"
    )
    owner_watermark = "https://p3-sign.douyinpic.com/owner-copy.webp"

    metadata = _metadata_from_aweme_detail(
        {
            "aweme_id": "7594083117851200612",
            "images": [
                {
                    "download_url_list": [watermarked],
                    "owner_watermark_image": {"url_list": [owner_watermark]},
                }
            ],
        }
    )

    assert metadata is not None
    assert metadata.images[0].source_urls == (watermarked, owner_watermark)


def test_select_douyin_metadata_prefers_live_motion_over_mobile_stills() -> None:
    mobile_stills = _metadata_from_aweme_detail(
        {
            "aweme_id": "7663513020283745856",
            "images": [
                {"url_list": ["https://p.example/one.webp"]},
                {"url_list": ["https://p.example/two.webp"]},
            ],
        }
    )
    live_detail = _metadata_from_aweme_detail(
        {
            "aweme_id": "7663513020283745856",
            "images": [
                {
                    "url_list": ["https://p.example/one.webp"],
                    "video": {
                        "play_addr": {"url_list": ["https://v.example/one.mp4"]}
                    },
                },
                {"url_list": ["https://p.example/two.webp"]},
            ],
        }
    )
    unrelated = _metadata_from_aweme_detail(
        {
            "aweme_id": "123",
            "video": {"play_addr": {"url_list": ["https://v.example/other.mp4"]}},
        }
    )

    selected = _select_douyin_metadata(
        [mobile_stills, unrelated, live_detail],
        expected_media_id="7663513020283745856",
    )

    assert selected is live_detail
    assert selected is not None
    assert selected.images[0].motion_urls == ("https://v.example/one.mp4",)


def test_metadata_from_mobile_share_html_reads_router_data() -> None:
    payload = {
        "loaderData": {
            "video_layout": None,
            "video_(id)/page": {
                "videoInfoRes": {
                    "item_list": [
                        {
                            "aweme_id": "7662035645020724465",
                            "desc": "测试移动端分享页",
                            "video": {
                                "duration": 1325117,
                                "play_addr": {
                                    "url_list": [
                                        "https://aweme.snssdk.com/aweme/v1/play/?video_id=test"
                                    ]
                                },
                            },
                        }
                    ]
                }
            },
        }
    }
    html = f"<script>window._ROUTER_DATA = {json.dumps(payload)}</script>"

    metadata = _metadata_from_mobile_share_html(html, "7662035645020724465")

    assert metadata is not None
    assert metadata.id == "7662035645020724465"
    assert metadata.title == "测试移动端分享页"
    assert metadata.duration == 1325.117
    assert metadata.source_urls == (
        "https://aweme.snssdk.com/aweme/v1/play/?video_id=test",
    )


def test_metadata_from_mobile_share_html_rejects_wrong_video() -> None:
    payload = {
        "loaderData": {
            "video_(id)/page": {
                "videoInfoRes": {
                    "item_list": [
                        {
                            "aweme_id": "123",
                            "video": {
                                "play_addr": {"url_list": ["https://cdn.example/123.mp4"]}
                            },
                        }
                    ]
                }
            }
        }
    }
    html = f"<script>window._ROUTER_DATA = {json.dumps(payload)}</script>"

    assert _metadata_from_mobile_share_html(html, "456") is None


def test_metadata_from_react_flight_scripts_reads_douyin_live_gallery() -> None:
    detail = {
        "awemeId": "7587447081268047268",
        "itemTitle": "今天吃苹果了吗",
        "isSlides": True,
        "images": [
            {
                "width": 1440,
                "height": 1920,
                "downloadUrlList": ["https://p.example/one.webp"],
                "urlList": ["https://p.example/one-preview.webp"],
                "video": {
                    "playAddr": [
                        {"src": "https://v.example/one.mp4"},
                        {"src": "https://v.example/one-backup.mp4"},
                    ]
                },
                "livePhotoType": 1,
            },
            {
                "urlList": ["https://p.example/two.webp"],
                "livePhotoType": 0,
            },
        ],
    }
    flight_payload = [
        "$",
        "$L9",
        None,
        {"awemeId": detail["awemeId"], "aweme": {"detail": detail}},
    ]
    serialized = f"7:{json.dumps(flight_payload)}\n"
    script = f"self.__pace_f.push({json.dumps([1, serialized])})"

    metadata = _metadata_from_react_flight_scripts(
        ["self.__pace_f.push([1,\"0:$L1\\n\"])", script],
        "7587447081268047268",
    )

    assert metadata is not None
    assert metadata.kind is MediaKind.IMAGES
    assert metadata.id == "7587447081268047268"
    assert metadata.title == "今天吃苹果了吗"
    assert len(metadata.images) == 2
    assert metadata.images[0].source_urls == (
        "https://p.example/one.webp",
        "https://p.example/one-preview.webp",
    )
    assert metadata.images[0].motion_urls == (
        "https://v.example/one.mp4",
        "https://v.example/one-backup.mp4",
    )
    assert not metadata.images[1].is_live
