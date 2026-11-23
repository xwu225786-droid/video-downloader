from __future__ import annotations

from fastapi import APIRouter, Request

from voxpull.api.schemas import StorageLocationResponse, SystemComponent, SystemStatusResponse
from voxpull.domain.errors import StorageLocationError
from voxpull.domain.models import ComponentStatus
from voxpull.infrastructure.directory_picker import DirectoryPickerError
from voxpull.infrastructure.storage import LocalStorage


router = APIRouter(prefix="/api", tags=["system"])


def _component(value: ComponentStatus) -> SystemComponent:
    return SystemComponent(ready=value.ready, detail=value.detail)


def _storage_location_response(
    storage: LocalStorage,
    *,
    changed: bool,
) -> StorageLocationResponse:
    return StorageLocationResponse(
        changed=changed,
        media_root_path=str(storage.media_root.resolve()),
        video_storage_path=str(storage.videos_root.resolve()),
        image_storage_path=str(storage.images_root.resolve()),
    )


@router.get("/system", response_model=SystemStatusResponse)
async def system_status(request: Request) -> SystemStatusResponse:
    container = request.app.state.container
    snapshot = await container.system_service.status()
    speech = getattr(container, "transcription_provider", None)
    cloud = bool(speech and speech.status()["cloud"])
    ready = snapshot.ready if not cloud else all(value.ready for value in (
        snapshot.playwright, snapshot.chromium, snapshot.cookie, snapshot.yt_dlp, snapshot.ffmpeg))
    return SystemStatusResponse(
        ready=ready,
        transcription_cloud=cloud,
        video_storage_path=str(container.storage.videos_root.resolve()),
        image_storage_path=str(container.storage.images_root.resolve()),
        python=_component(snapshot.python),
        playwright=_component(snapshot.playwright),
        chromium=_component(snapshot.chromium),
        cookie=_component(snapshot.cookie),
        yt_dlp=_component(snapshot.yt_dlp),
        ffmpeg=_component(snapshot.ffmpeg),
        whisper_cpp=_component(snapshot.whisper_cpp),
        model=_component(snapshot.model),
        vad_model=_component(snapshot.vad_model),
    )


@router.post("/storage/location", response_model=StorageLocationResponse)
async def change_storage_location(request: Request) -> StorageLocationResponse:
    container = request.app.state.container
    if container.job_service.has_active_jobs():
        raise StorageLocationError("任务处理期间不能更改保存位置，请等待当前任务完成")
    try:
        selected = await container.directory_picker.choose(container.storage.media_root)
        if selected is None:
            return _storage_location_response(container.storage, changed=False)
        container.storage.update_media_root(selected)
    except (DirectoryPickerError, OSError) as exc:
        raise StorageLocationError(
            "无法使用所选文件夹，请确认文件夹存在且允许写入",
            detail=str(exc),
        ) from exc
    return _storage_location_response(container.storage, changed=True)
