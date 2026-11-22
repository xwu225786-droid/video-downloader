"""Durable material labels, independent of legacy in-memory task records."""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from voxpull.infrastructure.file_lock import lock_file, unlock_file

from voxpull.infrastructure.cookies import save_storage_state


class MaterialTagStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(".lock").open("a") as lock:
            lock_file(lock)
            try:
                data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {"tags": [], "assignments": {}}
                yield data
            finally:
                unlock_file(lock)

    def read(self):
        with self._locked() as data:
            return data

    def create(self, name: str):
        name = " ".join(name.split())
        if not name or len(name) > 40:
            raise ValueError("标签名称请输入1至40个字符")
        with self._locked() as data:
            for tag in data["tags"]:
                if tag["name"].casefold() == name.casefold():
                    return tag
            tag = {"id": uuid4().hex, "name": name}
            data["tags"].append(tag)
            save_storage_state(self.path, data)
            return tag

    def assign(self, job_id: str, tag_ids: list[str], *, overwrite=False, expected_assignments=None):
        if len(tag_ids) > 1:
            raise ValueError("每个作品只能有一个标签")
        result = self.assign_many([job_id], tag_ids[0] if tag_ids else None,
                                  overwrite=overwrite, expected_assignments=expected_assignments)
        return {"job_id": job_id, "tag_ids": result["assignments"][job_id]}

    def assign_many(self, job_ids: list[str], tag_id: str | None, *,
                    overwrite=False, expected_assignments=None):
        job_ids = list(dict.fromkeys(job_ids))
        if not job_ids:
            raise ValueError("请先选择素材")
        with self._locked() as data:
            names = {tag["id"]: tag["name"] for tag in data["tags"]}
            if tag_id is not None and tag_id not in names:
                raise ValueError("标签不存在，请重新选择")
            desired = [tag_id] if tag_id is not None else []
            before = {ident: data["assignments"].get(ident, []) for ident in job_ids}
            conflicts = [
                {"job_id": ident, "tag_ids": values,
                 "tag_names": [names.get(value, "已有标签") for value in values]}
                for ident, values in before.items() if values and values != desired
            ]
            changed = overwrite and expected_assignments != before
            if len(job_ids) > 1 and ((conflicts and not overwrite) or changed):
                raise TagOverwriteRequired(conflicts, before, changed=changed)
            for ident in job_ids:
                if desired:
                    data["assignments"][ident] = desired.copy()
                else:
                    data["assignments"].pop(ident, None)
            save_storage_state(self.path, data)
            return {"assignments": {ident: desired.copy() for ident in job_ids},
                    "updated": len(job_ids)}

    def delete(self, tag_id: str, *, confirm=False, expected_job_ids=None):
        with self._locked() as data:
            tag = next((tag for tag in data["tags"] if tag["id"] == tag_id), None)
            if tag is None:
                raise KeyError(tag_id)
            job_ids = sorted(ident for ident, ids in data["assignments"].items() if tag_id in ids)
            changed = confirm and expected_job_ids != job_ids
            if (job_ids and not confirm) or changed:
                raise TagDeleteRequired(tag, job_ids, changed=changed)
            data["tags"] = [item for item in data["tags"] if item["id"] != tag_id]
            for ident in job_ids:
                remaining = [value for value in data["assignments"][ident] if value != tag_id]
                if remaining:
                    data["assignments"][ident] = remaining
                else:
                    data["assignments"].pop(ident)
            save_storage_state(self.path, data)
            return {**data, "deleted_tag_id": tag_id, "cleared_count": len(job_ids)}


class TagDeleteRequired(Exception):
    def __init__(self, tag, job_ids, *, changed=False):
        self.detail = {
            "code": "tag_delete_changed" if changed else "tag_delete_confirmation_required",
            "message": "标签关联的素材已变化，请重新确认" if changed else "该标签下已有素材，请确认是否删除",
            "tag": tag,
            "count": len(job_ids),
            "expected_job_ids": job_ids,
        }
        super().__init__(self.detail["message"])


class TagOverwriteRequired(Exception):
    def __init__(self, conflicts, expected_assignments, *, changed=False):
        self.detail = {
            "code": "tag_assignment_changed" if changed else "tag_overwrite_required",
            "message": "素材标签已发生变化，请确认最新标签后再覆盖" if changed else "部分素材已有标签，请确认是否覆盖",
            "conflicts": conflicts,
            "expected_assignments": expected_assignments,
        }
        super().__init__(self.detail["message"])
