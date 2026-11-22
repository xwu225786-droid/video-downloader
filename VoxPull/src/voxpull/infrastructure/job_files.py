"""Delete only files explicitly recorded in terminal task results."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field


class DeleteJobFilesRequest(BaseModel):
    job_ids: list[str] = Field(min_length=1, max_length=5000)
    protect_job_ids: list[str] = Field(default_factory=list, max_length=5000)


def result_files(job: dict[str, Any]) -> set[Path]:
    media = (job.get("result") or {}).get("media") or {}
    values = [media.get("cover_path"), media.get("title_path"), media.get("description_path"), *job.get("source_files", [])]
    if media.get("kind") == "video" and media.get("saved"):
        values.append(media.get("absolute_path"))
    values.extend(asset.get("absolute_path") for asset in media.get("assets", []))
    return {Path(value) for value in values if isinstance(value, str) and Path(value).is_absolute()}


async def delete_job_files(
    payload: DeleteJobFilesRequest,
    lookup: Callable[[str], Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    selected = set(payload.job_ids)
    protected = set(payload.protect_job_ids) - selected
    slots = asyncio.Semaphore(10)

    async def load(job_id: str) -> dict[str, Any]:
        async with slots:
            return await lookup(job_id)

    selected_jobs = await asyncio.gather(*(load(job_id) for job_id in selected))
    if any(job.get("status") not in {"completed", "failed", "paused"} for job in selected_jobs):
        raise HTTPException(409, "请等待任务处理结束后再删除")
    paths = set().union(*(result_files(job) for job in selected_jobs))
    protected_jobs = await asyncio.gather(*(load(job_id) for job_id in protected)) if paths else []
    if any(job.get("status") in {"queued", "running"} for job in protected_jobs):
        raise HTTPException(409, "请等待当前处理任务结束后再删除源文件；也可以仅删除记录")
    shared = set().union(*(result_files(job) for job in protected_jobs)) if protected_jobs else set()
    # Compare canonical locations too, but never follow links when deleting.
    shared = {path.resolve() for path in shared}
    retained = {path for path in paths if path.resolve() in shared}
    targets = paths - retained
    for path in targets:
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise HTTPException(409, "源文件路径包含符号链接，已停止删除")
        if path.exists() and not path.is_file():
            raise HTTPException(409, "源文件路径不是普通文件，已停止删除")
    deleted = missing = 0
    for path in sorted(targets):
        try:
            path.unlink()
            deleted += 1
        except FileNotFoundError:
            missing += 1
        except OSError as exc:
            raise HTTPException(409, f"已删除 {deleted} 个文件，部分文件删除失败；任务记录仍保留，请检查权限后重试") from exc
    return {"deleted_files": deleted, "shared_files": len(retained), "missing_files": missing}
