from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from voxpull.infrastructure.cloud_transcriber import SILICONFLOW_BASE, SILICONFLOW_MODEL

router = APIRouter(prefix='/api/transcription', tags=['transcription'])


class SpeechConfigRequest(BaseModel):
    provider: str = 'local'
    base_url: str = SILICONFLOW_BASE
    model: str = SILICONFLOW_MODEL
    api_key: str = ''


@router.get('/config')
async def get_config(request: Request):
    return request.app.state.container.transcription_provider.status()


@router.put('/config')
async def put_config(payload: SpeechConfigRequest, request: Request):
    return request.app.state.container.transcription_provider.configure(**payload.model_dump())


@router.delete('/config', status_code=204)
async def clear_config(request: Request):
    request.app.state.container.transcription_provider.clear()
    return Response(status_code=204)


@router.post('/models')
async def list_models(payload: SpeechConfigRequest, request: Request):
    models = await request.app.state.container.transcription_provider.list_models(**payload.model_dump())
    return {"models": models}


@router.post('/test')
async def test_connection(payload: SpeechConfigRequest, request: Request):
    return await request.app.state.container.transcription_provider.test_connection(**payload.model_dump())
