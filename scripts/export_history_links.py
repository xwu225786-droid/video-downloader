"""Export locally captured history cards after author-ID verification."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export_links(directory: Path) -> dict[str, int]:
    source = json.loads((directory / "搜索结果_原始快照.json").read_text(encoding="utf-8"))
    progress = json.loads((directory / "作者核验进度.json").read_text(encoding="utf-8"))
    verified = {item["url"]: item for item in progress["verified"]}
    target_path = progress["target_author_path"]
    collected, excluded, pending = [], [], []
    seen = set()
    for item in source["items"]:
        path = urlparse(item["url"]).path
        video = re.fullmatch(r"/video/(\d+)", path)
        author_label = item["label"].split("：", 1)[0]
        if not video:
            excluded.append({**item, "reason": "非视频作品"})
            continue
        if author_label != "李大霄":
            excluded.append({**item, "reason": "搜索结果显示发布者为其他作者"})
            continue
        evidence = verified.get(item["url"])
        if evidence is None:
            pending.append({**item, "reason": "尚未取得作品作者核验证据"})
            continue
        if urlparse(evidence["authorUrl"]).path != target_path:
            excluded.append({**item, "reason": "作品作者固定 ID 与目标作者不匹配"})
            continue
        video_id = video.group(1)
        if video_id in seen:
            continue
        seen.add(video_id)
        collected.append({
            "video_id": video_id,
            "url": f"https://www.douyin.com/video/{video_id}",
            "title": item["title"],
            "author": "李大霄",
            "author_sec_uid": target_path.rsplit("/", 1)[-1],
            "author_url": "https://www.douyin.com" + target_path,
            "author_badge": evidence.get("badge", ""),
            "author_verified_at": evidence["verifiedAt"],
            "history_evidence": item["label"],
            "download_status": "未开始",
            "transcription_status": "未开始",
        })

    missing = max(0, source["reported_count"] - len(source["items"]))
    totals = {
        "页面标示结果数": source["reported_count"],
        "实际读取链接数": len(source["items"]),
        "符合条件视频数": len(collected),
        "已排除记录数": len(excluded),
        "待核验记录数": len(pending),
        "标示数量差额": missing,
    }
    write_json(directory / "李大霄本人视频清单.json", {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "source": source["source"], "query": source["query"],
        "scope": "用户手动搜索后的抖音观看历史结果；只收录目标作者本人发布的视频",
        "counts": totals, "videos": collected,
    })
    (directory / "李大霄本人视频链接.txt").write_text(
        "\n".join(item["url"] for item in collected) + "\n", encoding="utf-8"
    )
    markdown = [
        "# 李大霄本人视频链接清单", "",
        f"已按固定账号 ID 逐条核验，共 {len(collected)} 条唯一视频链接。顺序沿用历史搜索结果，不代表观看时间或发布时间。",
        "", "本次仅收集链接，尚未下载视频或生成逐字稿。", "",
    ]
    for index, item in enumerate(collected, 1):
        title = item["title"].replace("[", "（").replace("]", "）").replace("\n", " ")
        markdown.append(f"{index}. [{title}]({item['url']})")
    (directory / "李大霄本人视频清单.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    write_json(directory / "排除记录.json", excluded)
    write_json(directory / "待核验记录.json", pending)
    report = [
        "# 观看历史链接收集报告", "", "筛选条件：自己的观看历史中，李大霄本人账号发布的视频。", "",
        f"目标作者：[李大霄](https://www.douyin.com{target_path})。固定账号 ID 通过用户给出的作品及每条视频详情页可见作者卡片核验。", "",
        *[f"- {name}：{count}" for name, count in totals.items()], "",
        "页面标示 68 条，但原始提取、滚动到列表底部和重新提交相同搜索后，页面始终只提供 67 个结果链接。差额 1 条没有可核对的链接或身份，本次不补造，原因未知。",
        "", "实际读到的结果中，53 条视频的作者固定 ID 均与目标作者一致；其余 14 条包括 13 条其他作者的作品和 1 篇文章。文章单独留在排除记录中。",
        "", "本次覆盖用户手动搜出的当前结果，不声称已恢复平台未返回、已清除或不可检索的全部历史。未取得观看时间或发布时间的字段不做推断。",
        "", "收集方式：通过已连接的 Chrome，读取观看历史页面上的链接，随后逐条打开候选视频详情页核验可见作者主页链接；不读取 Chrome Cookie 文件，不使用云端解析接口。",
        "", "先保存历史搜索快照，再进行作者核验；打开视频可能更新同一作品的最近观看时间，但不会改变已保存的源清单。",
        "", "本次未保存视频媒体文件，未启动语音转写。", "",
    ]
    (directory / "收集报告.md").write_text("\n".join(report), encoding="utf-8")
    return totals


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(export_links(args.directory), ensure_ascii=False, indent=2))
