from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import quote

import httpx

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse

from voxpull.api.schemas import (
    JobAcceptedResponse,
    JobCreateRequest,
    JobResponse,
    OpenLocationResponse,
    job_to_response,
)
from voxpull.api.auth import check_origin
from voxpull.domain.errors import MediaLocationError
from voxpull.domain.models import JobStatus, MediaKind
from voxpull.infrastructure.path_opener import PathOpenError
from voxpull.infrastructure.video_preview import video_file_response
from voxpull.infrastructure.publication import PublicationLookup
from voxpull.infrastructure.job_files import DeleteJobFilesRequest, delete_job_files


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/capabilities")
async def job_capabilities():
    return {"extract_txt": True, "xiaohongshu_guest": True, "material_folders": True,
            "pause": True, "douyin_guest_first": True, "douyin_best_quality": True}


@router.post("/{job_id}/pause", response_model=JobResponse)
async def pause_job(job_id: str, request: Request) -> JobResponse:
    check_origin(request)
    service = request.app.state.container.job_service
    job = service.get(job_id)
    if job is None:
        raise HTTPException(404, "任务不存在")
    if job.status.value not in {"queued", "running", "paused"}:
        raise HTTPException(409, "当前任务已结束，无需暂停")
    return job_to_response(await service.pause_job(job_id))


@router.post("/files/delete")
async def delete_files(payload: DeleteJobFilesRequest, request: Request):
    origin = request.headers.get("origin")
    origins = {str(request.base_url).rstrip("/")}
    legacy_port = getattr(request.app.state, "legacy_main_port", None)
    if legacy_port:
        origins.update({f"http://127.0.0.1:{legacy_port}", f"http://localhost:{legacy_port}"})
    if origin and origin not in origins:
        raise HTTPException(403, "仅允许从本地应用删除文件")

    async def lookup(job_id: str):
        job = request.app.state.container.job_service.get(job_id)
        if job is None:
            if legacy_port:
                async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
                    response = await client.get(f"http://127.0.0.1:{legacy_port}/api/jobs/{quote(job_id, safe='')}")
                if response.status_code == 200:
                    return response.json()
            raise HTTPException(404, "任务不存在，未删除文件")
        return {**job_to_response(job).model_dump(mode="json"),
                "source_files": job.metadata.get("source_files", [])}

    return await delete_job_files(payload, lookup)


@router.post("/{job_id}/retry", response_model=JobAcceptedResponse, status_code=202)
async def retry_job(job_id: str, request: Request) -> JobAcceptedResponse:
    service = request.app.state.container.job_service
    if service.get(job_id) is None or not service.get(job_id).content:
        raise HTTPException(404, "任务原链接需要由队列重新提交")
    queued_ahead = service.queue_size()
    job = service.retry_job(job_id)
    return JobAcceptedResponse(job_id=job.id, status=job.status.value, queued_ahead=queued_ahead)


@router.get("/{job_id}/transcript/status")
async def transcript_status(job_id: str, request: Request):
    service = request.app.state.container.job_service
    if service.get(job_id) is None:
        raise HTTPException(404, "任务不存在")
    return service.pipeline.subtitle_status(job_id)


@router.post("/{job_id}/transcript", response_model=JobResponse)
async def extract_transcript(job_id: str, request: Request, regenerate: bool = False):
    check_origin(request)
    service = request.app.state.container.job_service
    if service.get(job_id) is None:
        raise HTTPException(404, "任务不存在")
    return job_to_response(await service.pipeline.extract_saved_transcript(job_id, regenerate=regenerate))


@router.get("/{job_id}/publication")
async def get_job_publication(job_id: str, request: Request) -> dict[str, int | None]:
    job = request.app.state.container.job_service.get(job_id)
    if job is None or job.result is None:
        raise HTTPException(status_code=404, detail="任务结果不存在")
    stamp = job.result.media.published_at
    if stamp is None:
        if not hasattr(request.app.state, "publication_lookup"):
            request.app.state.publication_lookup = PublicationLookup()
        stamp = await request.app.state.publication_lookup.get(job.result.media.id)
    return {"published_at": stamp}


@router.api_route("/{job_id}/video", methods=["GET", "HEAD"], response_class=FileResponse)
async def preview_job_video(job_id: str, request: Request) -> FileResponse:
    job = request.app.state.container.job_service.get(job_id)
    if (
        job is None
        or job.result is None
        or job.result.media.kind is not MediaKind.VIDEO
        or (not job.result.media.saved and job.status is not JobStatus.RUNNING)
    ):
        raise HTTPException(status_code=404, detail="此任务没有保留可预览的视频")
    return video_file_response(Path(job.result.media.absolute_path))


@router.post("", response_model=JobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(payload: JobCreateRequest, request: Request) -> JobAcceptedResponse:
    service = request.app.state.container.job_service
    queued_ahead = service.queue_size()
    job = service.submit(payload.content, payload.language, payload.save_video, payload.extract_txt,
                         metadata={"auto_summary": payload.auto_summary and payload.extract_txt})
    return JobAcceptedResponse(job_id=job.id, status=job.status.value, queued_ahead=queued_ahead)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, request: Request) -> JobResponse:
    job = request.app.state.container.job_service.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job_to_response(job)


@router.post("/{job_id}/open-location", response_model=OpenLocationResponse)
async def open_job_location(job_id: str, request: Request) -> OpenLocationResponse:
    container = request.app.state.container
    job = container.job_service.get(job_id)
    if job is None or job.result is None:
        raise HTTPException(status_code=404, detail="任务结果不存在")
    media = job.result.media
    candidates = [Path(value) for value in (media.title_path, media.cover_path, media.description_path) if value]
    folder = Path(media.absolute_path) if media.kind is MediaKind.IMAGES else (
        candidates[0].parent if candidates else Path(media.absolute_path).parent
    )
    if not folder.is_dir():
        raise MediaLocationError("作品文件夹不存在或已删除")
    try:
        await container.path_opener.reveal(folder)
    except (PathOpenError, OSError) as exc:
        raise MediaLocationError(
            "无法打开文件夹，请确认文件仍在原位置",
            detail=str(exc),
        ) from exc
    return OpenLocationResponse(opened=True)


@router.get("/{job_id}/cover", response_class=FileResponse)
async def get_job_cover(job_id: str, request: Request) -> FileResponse:
    return _video_detail_response(job_id, request, "cover_path", "image/jpeg")


@router.get("/{job_id}/title", response_class=FileResponse)
async def get_job_title(job_id: str, request: Request) -> FileResponse:
    return _video_detail_response(job_id, request, "title_path", "text/plain; charset=utf-8")


def _video_detail_response(
    job_id: str, request: Request, field: str, media_type: str
) -> FileResponse:
    job = request.app.state.container.job_service.get(job_id)
    if job is None or job.result is None:
        raise HTTPException(status_code=404, detail="任务结果不存在")
    value = getattr(job.result.media, field)
    if not value or not Path(value).is_file():
        raise HTTPException(status_code=404, detail="封面或标题文件不存在或已移动")
    path = Path(value)
    if field == "cover_path":
        media_type = mimetypes.guess_type(path.name)[0] or media_type
    response = FileResponse(
        path, filename=path.name, media_type=media_type, content_disposition_type="inline"
    )
    response.headers["Cache-Control"] = "private, no-cache"
    return response


@router.get("/{job_id}/assets/{asset_position}", response_class=FileResponse)
async def get_job_asset(job_id: str, asset_position: int, request: Request) -> FileResponse:
    job = request.app.state.container.job_service.get(job_id)
    if job is None or job.result is None:
        raise HTTPException(status_code=404, detail="任务结果不存在")
    assets = job.result.media.assets
    if asset_position < 0 or asset_position >= len(assets):
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    path = Path(assets[asset_position].absolute_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="媒体文件已移动或删除")
    response = FileResponse(
        path,
        filename=assets[asset_position].filename,
        content_disposition_type="inline",
    )
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response
