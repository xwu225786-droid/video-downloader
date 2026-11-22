import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from voxpull.infrastructure.material_tags import MaterialTagStore, TagDeleteRequired, TagOverwriteRequired

router = APIRouter(prefix="/api/material-tags", tags=["material-tags"])


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class TagAssignment(BaseModel):
    tag_ids: list[str] = Field(max_length=1)
    overwrite: bool = False
    expected_assignments: dict[str, list[str]] | None = None


class BulkTagAssignment(BaseModel):
    job_ids: list[str] = Field(min_length=1, max_length=5000)
    tag_id: str | None
    overwrite: bool = False
    expected_assignments: dict[str, list[str]] | None = None


class TagDeleteRequest(BaseModel):
    confirm: bool = False
    expected_job_ids: list[str] | None = None


def store(request: Request):
    return MaterialTagStore(request.app.state.container.settings.data_dir / "material-tags.json")


def check_origin(request: Request):
    origins = {str(request.base_url).rstrip("/")}
    legacy_port = getattr(request.app.state, "legacy_main_port", None)
    if legacy_port:
        origins.update({f"http://127.0.0.1:{legacy_port}", f"http://localhost:{legacy_port}"})
    if request.headers.get("origin") and request.headers["origin"] not in origins:
        raise HTTPException(403, "请从本地应用设置标签")


@router.get("")
def get_tags(request: Request):
    return store(request).read()


@router.post("")
def create_tag(payload: TagCreate, request: Request):
    check_origin(request)
    try:
        return store(request).create(payload.name)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def validate_job_ids(job_ids):
    if any(not re.fullmatch(r"[a-f0-9]{32}", ident) for ident in job_ids):
        raise HTTPException(422, "素材编号无效")


@router.post("/bulk")
def assign_bulk_tags(payload: BulkTagAssignment, request: Request):
    check_origin(request)
    validate_job_ids(payload.job_ids)
    try:
        return store(request).assign_many(payload.job_ids, payload.tag_id,
                                         overwrite=payload.overwrite,
                                         expected_assignments=payload.expected_assignments)
    except TagOverwriteRequired as exc:
        raise HTTPException(409, exc.detail) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/{job_id}")
def assign_tags(job_id: str, payload: TagAssignment, request: Request):
    check_origin(request)
    validate_job_ids([job_id])
    try:
        return store(request).assign(job_id, payload.tag_ids, overwrite=payload.overwrite,
                                    expected_assignments=payload.expected_assignments)
    except TagOverwriteRequired as exc:
        raise HTTPException(409, exc.detail) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/{tag_id}/delete")
def delete_tag(tag_id: str, payload: TagDeleteRequest, request: Request):
    check_origin(request)
    try:
        return store(request).delete(tag_id, confirm=payload.confirm,
                                     expected_job_ids=payload.expected_job_ids)
    except TagDeleteRequired as exc:
        raise HTTPException(409, exc.detail) from exc
    except KeyError as exc:
        raise HTTPException(404, "标签不存在，请刷新后重试") from exc
