import pytest

from voxpull.application.pipeline import (
    extract_douyin_url,
    extract_url,
    validate_douyin_url,
    validate_url,
)
from voxpull.domain.errors import InvalidInputError, UnsupportedUrlError


def test_extracts_url_from_share_text() -> None:
    text = "复制打开抖音，看看这个作品 https://v.douyin.com/AbC123/ 更多内容"
    assert extract_douyin_url(text) == "https://v.douyin.com/AbC123/"


def test_strips_chinese_punctuation() -> None:
    assert extract_douyin_url("https://v.douyin.com/a1。") == "https://v.douyin.com/a1"


def test_accepts_direct_video_url_from_another_host() -> None:
    url = (
        "https://vod.dkhs.com/70f170687b9271f1b28e5017f0e80202/"
        "64bec20e052040189950279df8cb1a54-707ae0c22689553c33de4f9366a782aa-ld.mp4"
    )
    assert extract_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "https://douyin.com.evil.example/video/1",
        "https://evil-douyin.com/video/1",
    ],
)
def test_rejects_non_douyin_urls_from_douyin_only_validator(url: str) -> None:
    with pytest.raises(UnsupportedUrlError):
        validate_douyin_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/video",
        "https://user:pass@douyin.com/video/1",
        "https://douyin.com:8080/video/1",
    ],
)
def test_rejects_unsupported_urls(url: str) -> None:
    with pytest.raises((UnsupportedUrlError, InvalidInputError)):
        validate_url(url)


def test_rejects_missing_url() -> None:
    with pytest.raises(InvalidInputError):
        extract_douyin_url("这里只有文字")
