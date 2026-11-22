from typing import Annotated

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from voxpull.api.schemas import job_to_response
from voxpull.infrastructure.material_search import MaterialSearchService

router = APIRouter(prefix="/api/material-search", tags=["material-search"])
JobId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
SearchText = Annotated[str, Field(max_length=500_000)]


class SearchRequest(BaseModel):
    query: str = Field(max_length=500)
    job_ids: list[JobId] = Field(max_length=5000)
    titles: dict[JobId, Annotated[str, Field(max_length=4096)]] = Field(default_factory=dict)
    edits: dict[JobId, SearchText] = Field(default_factory=dict)


@router.post("")
async def search_materials(payload: SearchRequest, request: Request):
    origins = {str(request.base_url).rstrip("/")}
    legacy_port = getattr(request.app.state, "legacy_main_port", None)
    if legacy_port:
        origins.update({f"http://127.0.0.1:{legacy_port}", f"http://localhost:{legacy_port}"})
    if request.headers.get("origin") and request.headers["origin"] not in origins:
        raise HTTPException(403, "请从本机应用搜索素材")
    if not hasattr(request.app.state, "material_search"):
        request.app.state.material_search = MaterialSearchService()
    async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
        async def lookup(ident):
            job = request.app.state.container.job_service.get(ident)
            if job is not None:
                return {**job_to_response(job).model_dump(mode="json"), "title": job.metadata.get("title", "")}
            if legacy_port:
                try:
                    response = await client.get(f"http://127.0.0.1:{legacy_port}/api/jobs/{ident}")
                    if response.status_code == 200:
                        return response.json()
                except httpx.HTTPError:
                    pass
            return None

        return await request.app.state.material_search.search(payload.job_ids, payload.query,
                                                              payload.titles, payload.edits, lookup)
