"""Plan and reversibly move an existing material library without replacing files."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
from pathlib import Path

from voxpull.domain.naming import compact_media_id
from voxpull.infrastructure.material_folders import folder_title, read_index


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def job_paths(job: dict) -> set[Path]:
    media = (job.get("result") or {}).get("media") or {}
    values = [media.get(key) for key in ("absolute_path", "cover_path", "title_path", "description_path")]
    values += [a.get("absolute_path") for a in media.get("assets", [])]
    values += job.get("metadata", {}).get("source_files", [])
    return {Path(v) for v in values if isinstance(v, str) and Path(v).is_absolute()}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def plan_reorganization(videos_root: Path, images_root: Path, jobs: dict[str, dict]) -> dict:
    groups = []
    indexes = {}
    for root, kind in ((videos_root, "video"), (images_root, "images")):
        entries = copy.deepcopy(read_index(root))
        indexes[str(root)] = entries
        flat = [p for p in root.iterdir() if p.is_file() and not p.name.startswith(".")]
        grouped = {}
        if kind == "video":
            stems = {p.name.removesuffix(".title.txt") for p in flat if p.name.endswith(".title.txt")}
            stems |= {p.stem for p in flat if p.suffix.lower() == ".mp4"}
            for path in flat:
                stem = next((stem for stem in sorted(stems, key=len, reverse=True)
                             if path.name == stem or path.name.startswith(stem + ".") or path.name.startswith(stem + "_")), None)
                if stem is None:
                    raise ValueError(f"无法确定文件所属作品，未移动：{path.name}")
                grouped[stem] = [*grouped.get(stem, []), path]
            for stem, files in grouped.items():
                title_file = root / f"{stem}.title.txt"
                groups.append({"root": root, "kind": kind, "old": None, "files": files,
                    "stem": stem, "title": title_file.read_text(encoding="utf-8-sig") if title_file.is_file() else ""})
        elif flat:
            raise ValueError("图片父目录存在未归属文件，未移动")
        for folder in root.iterdir():
            if not folder.is_dir() or folder.name.startswith("."):
                continue
            manifest = _json(folder / "manifest.json")
            title_files = [folder / "标题.txt", *folder.glob("*.title.txt")]
            title = next((p.read_text(encoding="utf-8-sig") for p in title_files if p.is_file()), "")
            groups.append({"root": root, "kind": kind, "old": folder,
                "files": [p for p in folder.rglob("*") if p.is_file()],
                "stem": folder.name, "title": title or manifest.get("title", ""), "manifest": manifest})
    used = {str(root): {p.name.casefold() for p in root.iterdir()} for root in (videos_root, images_root)}
    mapping, writes, updated = {}, {}, copy.deepcopy(jobs)
    directories, moves = [], []
    for group in groups:
        root, old, files = group["root"], group["old"], group["files"]
        selected = {ident: job for ident, job in jobs.items() if job_paths(job).intersection(files)
                    or (old and any(p == old or old in p.parents for p in job_paths(job)))}
        ordered = sorted(selected, key=lambda ident: jobs[ident].get("created_at", ""), reverse=True)
        media = next(((jobs[i].get("result") or {}).get("media") for i in ordered
                      if (jobs[i].get("result") or {}).get("media")), {})
        title = group["title"] or media.get("title") or f"未命名作品 {group['stem']}"
        existing_identity = next((key for key, entry in indexes[str(root)].items()
                                  if old and entry["folder"] == old.name), None)
        identity = existing_identity or (group.get("manifest") or {}).get("id")
        if not identity and group["kind"] == "video":
            for candidate in (media.get("id"), f"{media.get('id')}_douyin-internal-v1"):
                if candidate and compact_media_id(candidate) == group["stem"]:
                    identity = candidate
                    break
        identity = identity or "@stem:" + group["stem"]
        entries = indexes[str(root)]
        indexed = next((value for key, value in entries.items()
                        if key == identity or key == "@stem:" + group["stem"]), None)
        if indexed and old == root / indexed["folder"]:
            target = old
        else:
            base = folder_title(title, identity)
            name, number = base, 0
            while name.casefold() in used[str(root)] and root / name != old:
                number += 1
                name = f"{base} ({compact_media_id(identity)}{f'-{number}' if number > 1 else ''})"
            target = root / name
            used[str(root)].add(name.casefold())
        entries[identity] = {"folder": target.name, "title": title}
        if group["kind"] == "video" and not old:
            entries["@stem:" + group["stem"]] = {"folder": target.name, "title": title}
        if old != target:
            if old:
                moves.append([str(old), str(target)])
                mapping[str(old)] = str(target)
            else:
                directories.append(str(target))
                for path in files:
                    destination = target / path.name
                    moves.append([str(path), str(destination)])
                    mapping[str(path)] = str(destination)
        existing = {str(target / p.relative_to(old)) if old else str(target / p.name): p for p in files}
        title_path = next((Path(name) for name in existing if name.endswith(".title.txt") or Path(name).name == "标题.txt"), target / "标题.txt")
        if str(title_path) not in existing:
            writes[str(title_path)] = title
        text_paths = {}
        text_variants = {}
        for ident in ordered:
            result = jobs[ident].get("result") or {}
            text = (result.get("transcript") or {}).get("text") if group["kind"] == "video" else (result.get("media") or {}).get("description")
            if text is None or text == "":
                continue
            if text not in text_variants:
                name = "文案.txt" if not text_variants else f"文案-{ident[:8]}.txt"
                text_path = target / name
                # Existing user-authored text is never overwritten.
                if str(text_path) not in existing:
                    writes[str(text_path)] = text
                text_variants[text] = str(text_path)
            text_paths[ident] = text_variants[text]
        description = (group.get("manifest") or {}).get("description")
        if description and not text_variants and str(target / "文案.txt") not in existing:
            writes[str(target / "文案.txt")] = description
        all_files = list(dict.fromkeys([*existing, str(title_path), *(p for p in writes if Path(p).parent == target)]))
        for ident in selected:
            updated[ident] = _rewrite_paths(updated[ident], mapping)
            result_media = (updated[ident].get("result") or {}).get("media")
            if result_media:
                result_media["title_path"] = str(title_path)
                if group["kind"] == "images":
                    result_media["absolute_path"] = str(target)
                    result_media["filename"] = target.name
                    if str(target / "文案.txt") in existing or str(target / "文案.txt") in writes:
                        result_media["description_path"] = str(target / "文案.txt")
                elif not result_media.get("saved"):
                    result_media["absolute_path"] = str(target / result_media["filename"])
                if ident in text_paths:
                    result_media["description_path"] = text_paths[ident]
            updated[ident].setdefault("metadata", {})["source_files"] = all_files
        group.update(title=title, identity=identity, target=target, job_ids=list(selected))
    # Some tasks reference multiple paths; apply the complete mapping in a final pass.
    updated = {ident: _rewrite_paths(job, mapping) for ident, job in updated.items()}
    inventory = {str(p): {"size": p.stat().st_size, "sha256": digest(p)}
                 for group in groups for p in group["files"]}
    return {"version": 1, "moves": moves, "directories": directories, "writes": writes,
            "indexes": indexes, "inventory": inventory, "jobs": updated,
            "groups": [{key: str(g[key]) if isinstance(g[key], Path) else g[key]
                        for key in ("kind", "title", "identity", "target", "job_ids")} for g in groups],
            "original_indexes": {str(root): (root / ".material-folders.json").read_text(encoding="utf-8") if (root / ".material-folders.json").exists() else None
                                 for root in (videos_root, images_root)}}


def _rewrite_paths(value, mapping):
    if isinstance(value, dict):
        return {key: _rewrite_paths(item, mapping) for key, item in value.items()}
    if isinstance(value, list):
        return [_rewrite_paths(item, mapping) for item in value]
    if isinstance(value, str) and value.startswith("/"):
        if value in mapping:
            return mapping[value]
        for old, new in sorted(mapping.items(), key=lambda pair: len(pair[0]), reverse=True):
            if value.startswith(old + "/"):
                return new + value[len(old):]
    return value


def apply_reorganization(plan: dict, journal_path: Path) -> None:
    for name, info in plan["inventory"].items():
        path = Path(name)
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError("源文件包含符号链接，未移动")
        if not path.is_file() or path.stat().st_size != info["size"] or digest(path) != info["sha256"]:
            raise ValueError("素材文件在规划后发生变化，未移动")
    for old, new in plan["moves"]:
        if Path(new).exists():
            raise ValueError("目标路径已存在，未覆盖")
    for root, original in plan["original_indexes"].items():
        path = Path(root) / ".material-folders.json"
        if (path.read_text(encoding="utf-8") if path.exists() else None) != original:
            raise ValueError("文件夹索引在规划后发生变化，未移动")
    for name in plan.get("copies", {}):
        if Path(name).exists():
            raise ValueError("封面目标已存在，未覆盖")
    journal = {"moves": [], "writes": [], "directories": [], "indexes": [], "edits": [], "complete": False}
    def save():
        journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")
        journal_path.chmod(0o600)
    save()
    try:
        for name in plan["directories"]:
            Path(name).mkdir(exist_ok=False)
            journal["directories"].append(name)
            save()
        for old, new in plan["moves"]:
            os.rename(old, new)
            journal["moves"].append([old, new])
            save()
        for name, content in plan["writes"].items():
            with Path(name).open("x", encoding="utf-8") as handle:
                handle.write(content)
            journal["writes"].append(name)
            save()
        for name, source in plan.get("copies", {}).items():
            with Path(name).open("xb") as destination, Path(source).open("rb") as original:
                shutil.copyfileobj(original, destination)
            journal["writes"].append(name)
            save()
        for name, edit in plan.get("edits", {}).items():
            if Path(name).read_text(encoding="utf-8") != edit["before"]:
                raise ValueError("素材清单已发生变化，未覆盖")
            journal["edits"].append([name, edit["before"]])
            save()
            Path(name).write_text(edit["after"], encoding="utf-8")
        for root, entries in plan["indexes"].items():
            path = Path(root) / ".material-folders.json"
            journal["indexes"].append([str(path), plan["original_indexes"][root]])
            save()
            temporary = path.with_suffix(".json.migration-tmp")
            temporary.write_text(json.dumps({"version": 1, "materials": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.chmod(0o600)
            os.replace(temporary, path)
        for old, info in plan["inventory"].items():
            new = _rewrite_paths(old, dict(plan["moves"]))
            expected = info["sha256"]
            if new in plan.get("edits", {}):
                expected = hashlib.sha256(plan["edits"][new]["after"].encode("utf-8")).hexdigest()
            if digest(Path(new)) != expected:
                raise ValueError("移动后的文件校验失败")
        journal["complete"] = True
        save()
    except BaseException:
        rollback_reorganization(journal_path)
        raise


def rollback_reorganization(journal_path: Path) -> None:
    journal = _json(journal_path)
    for name, original in reversed(journal.get("indexes", [])):
        path = Path(name)
        if original is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(original, encoding="utf-8")
            path.chmod(0o600)
    for name, original in reversed(journal.get("edits", [])):
        Path(name).write_text(original, encoding="utf-8")
    for name in reversed(journal.get("writes", [])):
        Path(name).unlink(missing_ok=True)
    for old, new in reversed(journal.get("moves", [])):
        if Path(new).exists() and not Path(old).exists():
            os.rename(new, old)
    for name in reversed(journal.get("directories", [])):
        if Path(name).exists():
            Path(name).rmdir()
    journal["rolled_back"] = True
    journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")


def plan_friendly_names(videos_root: Path, images_root: Path, jobs: dict[str, dict]) -> dict:
    """Rename already-organized material files while preserving all media bytes."""
    import re
    moves, mapping, copies, edits, groups, inventory = [], {}, {}, {}, [], {}
    for root, kind in ((videos_root, "video"), (images_root, "images")):
        for folder in root.iterdir():
            if not folder.is_dir() or folder.name.startswith("."):
                continue
            files = [p for p in folder.rglob("*") if p.is_file()]
            selected = [ident for ident, job in jobs.items()
                        if any(p == folder or folder in p.parents for p in job_paths(job))]
            images = []
            for source in files:
                name = source.name
                if kind == "video":
                    if source.suffix.lower() == ".mp4":
                        name = "视频.mp4"
                    elif source.name.endswith(".cover.jpg"):
                        name = "封面.jpg"
                    elif source.name.endswith(".title.txt"):
                        name = "标题.txt"
                else:
                    match = re.fullmatch(r"(\d+)(\.live)?(\.[^.]+)", source.name)
                    if match:
                        name = f"{'视频' if match[2] else '图片'}{int(match[1])}{match[3]}"
                    image = re.fullmatch(r"图片(\d+)\.[^.]+", name)
                    if image:
                        images.append((int(image[1]), source, folder / name))
                target = source.with_name(name)
                if target != source:
                    moves.append([str(source), str(target)])
                    mapping[str(source)] = str(target)
                inventory[str(source)] = {"size": source.stat().st_size, "sha256": digest(source)}
            if len({new for old, new in moves}) != len(moves):
                raise ValueError("作品内存在重名目标，未覆盖")
            if kind == "images":
                if images:
                    _, old_cover, new_cover_source = min(images)
                    cover = folder / ("封面" + new_cover_source.suffix)
                    if not cover.exists():
                        copies[str(cover)] = str(new_cover_source)
                else:
                    cover = None
                manifest_path = folder / "manifest.json"
                if manifest_path.is_file():
                    original = manifest_path.read_text(encoding="utf-8")
                    manifest = json.loads(original)
                    changed = False
                    for asset in manifest.get("assets", []):
                        for key in ("image", "motion"):
                            old_name = asset.get(key)
                            new = mapping.get(str(folder / old_name)) if old_name else None
                            if new:
                                asset[key] = Path(new).name
                                changed = True
                    if changed:
                        edits[str(manifest_path)] = {"before": original,
                            "after": json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"}
            else:
                cover = folder / "封面.jpg"
            groups.append({"target": str(folder), "kind": kind, "job_ids": selected,
                           "cover": str(cover) if cover else None})
    updated = _rewrite_paths(copy.deepcopy(jobs), mapping)
    for group in groups:
        for ident in group["job_ids"]:
            job = updated[ident]
            media = (job.get("result") or {}).get("media")
            if media:
                if media["kind"] == "video":
                    media["filename"] = "视频.mp4"
                    if not media.get("saved"):
                        media["absolute_path"] = str(Path(group["target"]) / "视频.mp4")
                for asset in media.get("assets", []):
                    asset["filename"] = Path(asset["absolute_path"]).name
                if group["cover"] and (Path(group["cover"]).is_file() or group["cover"] in copies):
                    media["cover_path"] = group["cover"]
            if group["cover"] in copies:
                metadata = job.setdefault("metadata", {})
                metadata["source_files"] = list(dict.fromkeys([*metadata.get("source_files", []), group["cover"]]))
    return {"version": 1, "moves": moves, "directories": [], "writes": {},
            "copies": copies, "edits": edits, "indexes": {}, "original_indexes": {},
            "inventory": inventory, "jobs": updated, "groups": groups}
