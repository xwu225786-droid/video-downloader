"""Isolated Douyin internal-playback trial; never changes existing job assets."""
# ruff: noqa: E402 -- resolve the adjacent source checkout before importing it.
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "VoxPull" / "src"))

from voxpull.application.pipeline import extract_url
from voxpull.domain.errors import VoxPullError
from voxpull.domain.models import MediaKind
from voxpull.infrastructure.browser import PlaywrightBrowser
from voxpull.infrastructure.downloader import YtDlpDownloader


async def run(content: str, login: bool) -> None:
    auth = ROOT / "VoxPull" / "data" / "auth"
    browser = PlaywrightBrowser(auth.parent / "browser-profile", auth / "storage-state.json", 30)
    try:
        if login:
            await browser.start_auth()
            await asyncio.to_thread(input, "请在打开的窗口中登录抖音，完成后按回车：")
            await browser.complete_auth()
        with tempfile.TemporaryDirectory(prefix="voxpull-internal-") as directory:
            work = Path(directory)
            print("正在读取抖音站内播放数据……", flush=True)
            evidence = await browser.acquire(extract_url(content), work / "cookies.txt")
            media = evidence.media
            if media is None or media.kind is not MediaKind.VIDEO:
                raise VoxPullError("此试用入口仅支持视频作品")
            if media.video_source_policy != "douyin-internal-v1":
                raise VoxPullError("未取得站内播放源，已停止下载")
            print("已取得站内播放源，正在下载……", flush=True)
            video = await YtDlpDownloader(120).download(
                evidence.final_url, media, evidence.cookie_file,
                evidence.user_agent, work, lambda *_: None,
            )
            output = ROOT / "无水印试跑" / f"{datetime.now():%Y%m%d_%H%M%S_%f}_{media.id}"
            output.mkdir(parents=True, exist_ok=False)
            shutil.copy2(video, output / "视频.mp4")
            (output / "标题.txt").write_text(media.title, encoding="utf-8")
            (output / "来源说明.json").write_text(json.dumps({
                "media_id": media.id, "title": media.title,
                "source_policy": media.video_source_policy,
                "source": "抖音站内播放数据；不使用分享页下载地址",
                "size_bytes": video.stat().st_size,
                "visual_watermark_checked": False,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"下载完成：{output / '视频.mp4'}", flush=True)
    finally:
        await browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="抖音站内播放源试下载，不修改原有任务")
    parser.add_argument("content", nargs="?", help="作品链接或完整分享文本")
    parser.add_argument("--login", action="store_true", help="先打开应用专用浏览器登录")
    args = parser.parse_args()
    try:
        content = args.content or input("请粘贴抖音作品链接或分享内容：").strip()
        asyncio.run(run(content, args.login))
        return 0
    except VoxPullError as exc:
        print(f"未完成：{exc.message}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
