from unittest.mock import AsyncMock

import httpx

from test_api import make_settings
from voxpull.app import create_app
from voxpull.domain.models import Job, JobBatch, JobStatus
from voxpull.infrastructure.video_preview import create_preview_bridge


async def test_auth_api_uses_worker_owned_browser_and_validates_target(tmp_path):
    app = create_app(make_settings(tmp_path))
    app.state.legacy_main_port = 18765
    browser = app.state.container.browser
    browser.start_auth = AsyncMock(return_value="verification_required")
    browser._pending_url = "https://www.douyin.com/video/123"
    browser._blocked = True
    browser._active = True
    browser._status = "verification_required"
    ident = "a" * 32
    app.state.container.job_service.repository.add(Job(ident, "https://v.douyin.com/short/", "zh", status=JobStatus.FAILED))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        headers = {"Origin": "http://127.0.0.1:18765"}
        cap = (await client.get('/api/auth/douyin/capabilities')).json()
        assert cap['version'] == 3 and cap['shared_session']
        result = await client.post('/api/auth/douyin/start', json={'job_id': ident}, headers=headers)
        assert result.status_code == 200
        assert result.json() == {'status': 'verification_required', 'target_url': 'https://www.douyin.com/video/123',
                                 'waiting_jobs': 1, 'session_shared': True, 'active_job': True}
        browser.start_auth.assert_awaited_once_with('https://v.douyin.com/short/')
        direct = 'https://www.douyin.com/video/123'
        assert (await client.post('/api/auth/douyin/start', json={'target_url': direct}, headers=headers)).status_code == 200
        browser.start_auth.assert_awaited_with(direct)
        assert (await client.post('/api/auth/douyin/start', json={'target_url': 'https://other.test/video'}, headers=headers)).status_code == 422
        assert (await client.post('/api/auth/douyin/start', json={'job_id': ident, 'target_url': direct}, headers=headers)).status_code == 422
        assert (await client.get('/api/auth/douyin/status')).json() == result.json()
        assert (await client.post('/api/auth/douyin/start', json={'job_id': ident}, headers={'Origin': 'https://external.test'})).status_code == 403
        assert (await client.post('/api/auth/douyin/start', json={'job_id': 'b'*32}, headers=headers)).status_code == 404
        assert (await client.post('/api/auth/douyin/start', json={'job_id': '../file'}, headers=headers)).status_code == 422
        other = 'c'*32
        app.state.container.job_service.repository.add(Job(other, 'https://example.test/video', 'zh'))
        assert (await client.post('/api/auth/douyin/start', json={'job_id': other}, headers=headers)).status_code == 422


async def test_legacy_auth_bridge_forwards_to_shared_owner_instead_of_opening_profile():
    app = create_preview_bridge(18765, 1, auth_backend_port=18767)
    captured = []
    async def handler(request):
        captured.append(request)
        if request.url.path.endswith('/capabilities'):
            return httpx.Response(200, json={'version': 3, 'shared_session': True})
        return httpx.Response(200, json={'status': 'verification_required', 'session_shared': True})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as owner:
        app.state.client = owner
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
            assert (await client.post('/api/auth/douyin/start')).status_code == 403
            response = await client.post('/api/auth/douyin/start', json={'job_id': 'a'*32}, headers={'Origin': 'http://127.0.0.1:18765'})
            assert response.json()['session_shared']
            assert captured[-1].url.port == 18767
            assert captured[-1].headers['origin'] == 'http://127.0.0.1:18765'
            assert b'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' in captured[-1].content
            assert (await client.get('/api/auth/douyin/capabilities')).json()['version'] == 3
            assert (await client.get('/api/auth/douyin/status')).json()['status'] == 'verification_required'
            assert not hasattr(app.state, 'auth_browser')


async def test_waiting_task_state_is_visible_in_single_and_batch_apis(tmp_path):
    app = create_app(make_settings(tmp_path))
    service = app.state.container.job_service
    batch = JobBatch("d"*32, ("a"*32, "b"*32), "zh", True)
    service._batches[batch.id] = batch
    for ident, state in zip(batch.job_ids, ['verification_required', 'waiting_browser']):
        service.repository.add(Job(ident, "https://www.douyin.com/video/123", "zh", status=JobStatus.RUNNING,
                                   metadata={"auth_status": state}, message="等待手动验证"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
        data = (await client.get('/api/batches/'+batch.id)).json()
        assert [j['auth_status'] for j in data['jobs']] == ['verification_required', 'waiting_browser']
        assert (await client.get('/api/jobs/'+batch.job_ids[0])).json()['auth_status'] == 'verification_required'
