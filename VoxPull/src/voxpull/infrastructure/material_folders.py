"""Stable title-named material directories with collision-safe identities."""
from __future__ import annotations

import fcntl
import json
import os
import re
import threading
import unicodedata
from pathlib import Path

from voxpull.domain.naming import compact_media_id

_lock = threading.RLock()
_INDEX = ".material-folders.json"


def folder_title(title: str, identity: str) -> str:
    value = unicodedata.normalize("NFC", title)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", value)
    value = " ".join(value.split()).strip(" .")
    # Leave room below the filesystem's 255-byte component limit for collision suffixes.
    value = value.encode("utf-8")[:180].decode("utf-8", errors="ignore").rstrip(" .")
    return value or f"未命名作品 {compact_media_id(identity)}"


def read_index(root: Path) -> dict:
    path = root / _INDEX
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data["materials"]
    if not isinstance(entries, dict):
        raise ValueError("素材文件夹索引无效，未覆盖现有索引")
    return entries


def _entry_folder(root: Path, entry: dict | None) -> Path | None:
    if not entry:
        return None
    name = entry["folder"]
    if not isinstance(name, str) or Path(name).name != name or name in {".", ".."}:
        raise ValueError("素材文件夹索引包含无效路径")
    path = root / name
    if path.is_symlink():
        raise ValueError("素材文件夹不能使用符号链接")
    return path


def find_material_folder(root: Path, identity: str) -> Path | None:
    entries = read_index(root)
    return _entry_folder(root, entries.get(identity) or entries.get("@stem:" + compact_media_id(identity)))


def ensure_material_folder(root: Path, identity: str, title: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    with _lock, (root / ".material-folders.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        entries = read_index(root)
        folder = _entry_folder(root, entries.get(identity) or entries.get("@stem:" + compact_media_id(identity)))
        if folder is None:
            base = folder_title(title, identity)
            number = 0
            while True:
                suffix = "" if not number else f" ({compact_media_id(identity)}{f'-{number}' if number > 1 else ''})"
                folder = root / (base + suffix)
                try:
                    folder.mkdir(exist_ok=False)
                    break
                except FileExistsError:
                    number += 1
        else:
            folder.mkdir(exist_ok=True)
        entries[identity] = {"folder": folder.name, "title": title}
        temporary = root / f"{_INDEX}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            temporary.write_text(json.dumps({"version": 1, "materials": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.chmod(0o600)
            os.replace(temporary, root / _INDEX)
        finally:
            temporary.unlink(missing_ok=True)
        return folder
