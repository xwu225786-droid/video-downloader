"""Read-only keyword search over task text and associated TXT sidecars."""
from __future__ import annotations

import asyncio
import unicodedata
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path


def normalized(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def document_from_job(data: dict) -> dict:
    result = data.get("result") or {}
    media = result.get("media") or {}
    return {
        "title": media.get("title") or data.get("title") or "",
        "text": "\n".join(filter(None, [media.get("description"), (result.get("transcript") or {}).get("text")])),
        "media": {key: media.get(key) for key in (
            "id", "kind", "filename", "absolute_path", "title_path", "description_path", "cover_path"
        )},
    }


def txt_paths(media: dict) -> list[Path]:
    paths = set()
    roots = set()
    stems = {str(media.get("id") or "")}
    for key in ("title_path", "description_path", "cover_path", "absolute_path"):
        value = media.get(key)
        if not value:
            continue
        path = Path(value)
        if not path.is_absolute():
            continue
        if key in {"title_path", "description_path"} and path.suffix.lower() == ".txt":
            paths.add(path)
        if key == "absolute_path" and media.get("kind") == "images":
            if path.is_dir():
                paths.update(p for p in path.iterdir() if p.is_file() and p.suffix.lower() == ".txt")
            continue
        roots.add(path.parent)
        if key == "absolute_path":
            stems.add(path.stem)
        elif key == "title_path":
            stems.add(path.name.removesuffix(".title.txt"))
        elif key == "cover_path":
            stems.add(path.name.removesuffix(".cover.jpg"))
    # Only files named for this material are included, not unrelated TXT in the directory.
    for root in roots:
        for stem in stems - {""}:
            if Path(stem).name != stem or stem in {".", ".."}:
                continue
            for suffix in (".txt", ".title.txt", ".transcript.txt", ".文案.txt", "_文案.txt", "_时间轴.txt"):
                candidate = root / f"{stem}{suffix}"
                if candidate.is_file():
                    paths.add(candidate)
    return sorted(paths)


@lru_cache(maxsize=512)
def read_txt(path: str, size: int, modified_ns: int) -> str:
    raw = Path(path).read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("gb18030")


def search_document(document: dict, query: str, title: str = "", edit: str = "") -> dict:
    terms = normalized(query).split()
    chunks = [("title", document["title"] or title), ("text", document["text"])]
    if edit:
        chunks.append(("text", edit))
    file_errors = []
    try:
        paths = txt_paths(document["media"])
    except OSError:
        paths = []
        file_errors.append("关联 TXT")
    for path in paths:
        try:
            stat = path.stat()
            chunks.append(("txt", read_txt(str(path), stat.st_size, stat.st_mtime_ns)))
        except (OSError, UnicodeError):
            file_errors.append(path.name)
    haystacks = [(field, text, normalized(text)) for field, text in chunks if text]
    if not all(any(term in text for _, _, text in haystacks) for term in terms):
        return {"matched": False, "file_errors": file_errors}
    fields = list(dict.fromkeys(field for field, _, text in haystacks if any(term in text for term in terms)))
    candidate = next((text for field, text, norm in haystacks if field != "title" and any(term in norm for term in terms)),
                     next((text for _, text, _ in haystacks), ""))
    display = " ".join(unicodedata.normalize("NFKC", candidate).split())
    offsets = [normalized(display).find(term) for term in terms if term in normalized(display)]
    offset = max(0, min(offsets, default=0) - 35)
    snippet = ("…" if offset else "") + display[offset:offset + 150]
    if offset + 150 < len(display):
        snippet += "…"
    return {"matched": True, "fields": fields, "snippet": snippet, "file_errors": file_errors}


class MaterialSearchService:
    def __init__(self):
        self.completed = OrderedDict()

    async def search(self, job_ids, query, titles, edits, lookup):
        slots = asyncio.Semaphore(8)

        async def find(ident):
            async with slots:
                document = self.completed.get(ident)
                if document is None:
                    data = await lookup(ident)
                    if data is None:
                        return ident, None
                    document = document_from_job(data)
                    if data.get("status") in {"completed", "failed", "paused"}:
                        self.completed[ident] = document
                        if len(self.completed) > 4096:
                            self.completed.popitem(last=False)
                else:
                    self.completed.move_to_end(ident)
                result = await asyncio.to_thread(search_document, document, query, titles.get(ident, ""), edits.get(ident, ""))
                return ident, result

        results = await asyncio.gather(*(find(ident) for ident in dict.fromkeys(job_ids)))
        return {
            "matches": [{"job_id": ident, "fields": result["fields"], "snippet": result["snippet"]}
                        for ident, result in results if result and result["matched"]],
            "searched_count": sum(result is not None for _, result in results),
            "unavailable_ids": [ident for ident, result in results if result is None],
            "file_error_count": sum(len(result["file_errors"]) for _, result in results if result),
        }
