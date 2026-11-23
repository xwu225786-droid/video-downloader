from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response, status

from voxpull.api.schemas import BatchCreateRequest, BatchResponse, batch_to_response, job_to_response
from voxpull.application.exporters import to_srt, to_timeline_text
from voxpull.application.pipeline import extract_batch_urls
from voxpull.domain.models import JobStatus


router = APIRouter(prefix="/api/batches", tags=["batches"])


@router.post("", response_model=BatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_batch(payload: BatchCreateRequest, request: Request) -> BatchResponse:
    service = request.app.state.container.job_service
    urls, duplicates = extract_batch_urls(payload.content)
    batch = service.submit_batch(urls, payload.language, payload.save_video, duplicates, payload.extract_txt,
                                 auto_summary=payload.auto_summary and payload.extract_txt)
    return batch_to_response(batch, service.batch_jobs(batch))


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(batch_id: str, request: Request) -> BatchResponse:
    service = request.app.state.container.job_service
    batch = service.get_batch(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="批次不存在，可能因服务重启已清除，请重新提交链接")
    return batch_to_response(batch, service.batch_jobs(batch))


@router.post("/{batch_id}/retry", response_model=BatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_batch(batch_id: str, request: Request) -> BatchResponse:
    service = request.app.state.container.job_service
    if service.get_batch(batch_id) is None:
        raise HTTPException(status_code=404, detail="批次不存在")
    batch = service.retry_batch(batch_id)
    return batch_to_response(batch, service.batch_jobs(batch))


@router.get("/{batch_id}/archive")
def download_batch_archive(batch_id: str, request: Request) -> Response:
    service = request.app.state.container.job_service
    batch = service.get_batch(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="批次不存在")
    jobs = service.batch_jobs(batch)
    if any(job.status in {JobStatus.QUEUED, JobStatus.RUNNING} for job in jobs):
        raise HTTPException(status_code=409, detail="请等待当前批次处理结束后再打包")
    output = io.BytesIO()
    missing_files = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index, job in enumerate(jobs, 1):
            if job.result is None:
                continue
            folder = f"{index:03d}_{job.id[:8]}"
            result = job.result
            archive.writestr(f"{folder}/标题.txt", result.media.title)
            archive.writestr(
                f"{folder}/元数据.json",
                json.dumps(job_to_response(job).model_dump(mode="json"), ensure_ascii=False, indent=2),
            )
            if result.media.description:
                archive.writestr(f"{folder}/文案.txt", result.media.description)
            if result.transcript is not None:
                archive.writestr(f"{folder}/逐字稿.txt", result.transcript.text)
                if result.transcript.segments:
                    archive.writestr(f"{folder}/时间轴.txt", to_timeline_text(result.transcript))
                    archive.writestr(f"{folder}/字幕.srt", to_srt(result.transcript))
            if result.media.cover_path:
                cover = Path(result.media.cover_path)
                if cover.is_file():
                    archive.write(cover, f"{folder}/封面.jpg")
                else:
                    missing_files.append({"job_id": job.id, "file": "封面.jpg", "reason": "文件已移动或删除"})
        manifest = batch_to_response(batch, jobs).model_dump(mode="json")
        manifest["missing_files"] = missing_files
        archive.writestr("批处理清单.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("说明.txt", "包含成功任务的逐字稿、时间轴、字幕、标题、封面和元数据。\n"
                         "视频原文件保存在所选本地目录，不包含在本压缩包中。\n"
                         "失败原因及缺失文件见批处理清单.json。\n")
    return Response(output.getvalue(), media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="batch-{batch.id[:12]}.zip"',
        "Cache-Control": "no-store",
    })
