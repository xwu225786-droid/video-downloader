from dataclasses import replace

from httpx import ASGITransport, AsyncClient

from test_api import completed_video_job, make_settings
from voxpull.app import create_app
from voxpull.domain.models import MediaKind
from voxpull.infrastructure.material_search import MaterialSearchService


async def test_search_title_body_txt_and_current_edits_without_changing_materials(tmp_path):
    app = create_app(make_settings(tmp_path))
    repo = app.state.container.job_service.repository
    video = completed_video_job("a" * 32)
    source = tmp_path / "video.mp4"
    source.write_bytes(b"original video")
    title = tmp_path / "video.title.txt"
    title.write_text("投资视频", encoding="utf-8-sig")
    subtitle = tmp_path / "video.txt"
    subtitle.write_text("TXT 独有关键词 长期价值", encoding="utf-16")
    (tmp_path / "other.txt").write_text("不属于素材的隐私内容")
    video.result = replace(video.result, media=replace(video.result.media, title="投资视频",
        absolute_path=str(source), title_path=str(title)))
    repo.add(video)
    gallery = completed_video_job("b" * 32)
    folder = tmp_path / "gallery"
    folder.mkdir()
    (folder / "文案.txt").write_text("图文 TXT 独有字段", encoding="gb18030")
    gallery.result = replace(gallery.result, media=replace(gallery.result.media,
        kind=MediaKind.IMAGES, title="图集", absolute_path=str(folder),
        description="图文原始正文 独有词"), transcript=None)
    repo.add(gallery)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        async def search(q, **kwargs):
            response = await client.post("/api/material-search", json={
                "query": q, "job_ids": [video.id, gallery.id], **kwargs})
            assert response.status_code == 200, response.text
            return response.json()
        assert (await search("投资"))["matches"][0]["job_id"] == video.id
        assert (await search("原始文案"))["matches"][0]["fields"] == ["text"]
        assert (await search("原始正文"))["matches"][0]["job_id"] == gallery.id
        hit = (await search("txt 长期价值"))["matches"]
        assert len(hit) == 1 and hit[0]["job_id"] == video.id and hit[0]["fields"] == ["txt"]
        assert "长期价值" in hit[0]["snippet"]
        assert (await search("投资 原始文案"))["matches"][0]["fields"] == ["title", "text", "txt"]
        assert (await search("独有字段"))["matches"][0]["job_id"] == gallery.id
        assert (await search("隐私内容"))["matches"] == []
        assert (await search("临时校对", edits={video.id: "临时校对内容"}))["matches"][0]["fields"] == ["text"]
        assert (await search("临时校对"))["matches"] == []
        assert (await search("不存在的词"))["matches"] == []
        assert (await search("ｔｘｔ"))["matches"]
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


async def test_search_refreshes_changed_txt_and_reports_missing_records_and_files(tmp_path):
    app = create_app(make_settings(tmp_path))
    job = completed_video_job("a" * 32)
    txt = tmp_path / "missing.title.txt"
    job.result = replace(job.result, media=replace(job.result.media, title_path=str(txt)))
    app.state.container.job_service.repository.add(job)
    payload = {"query": "更新内容", "job_ids": [job.id, "b" * 32, job.id]}
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        data = (await client.post("/api/material-search", json=payload)).json()
        assert data["searched_count"] == 1 and data["unavailable_ids"] == ["b" * 32]
        assert data["file_error_count"] == 1 and data["matches"] == []
        txt.write_text("更新内容", encoding="utf-8")
        data = (await client.post("/api/material-search", json=payload)).json()
        assert data["matches"][0]["job_id"] == job.id and data["file_error_count"] == 0
        txt.write_text("已经换成新内容", encoding="utf-8")
        assert not (await client.post("/api/material-search", json=payload)).json()["matches"]


async def test_search_live_jobs_are_not_cached_and_legacy_documents_are_supported():
    service = MaterialSearchService()
    data = {"status": "queued", "result": None}
    calls = []
    async def lookup(ident):
        calls.append(ident)
        return data
    ident = "c" * 32
    result = await service.search([ident], "标题", {ident: "未完成标题"}, {}, lookup)
    assert result["matches"][0]["fields"] == ["title"]
    data.update(status="completed", result={"media": {"title": "完成标题"},
                                         "transcript": {"text": "完成后文案"}})
    result = await service.search([ident], "完成后", {}, {}, lookup)
    assert result["matches"][0]["snippet"] == "完成后文案" and len(calls) == 2
    await service.search([ident], "完成后", {}, {}, lookup)
    assert len(calls) == 2


async def test_search_validates_request_and_local_origin(tmp_path):
    app = create_app(make_settings(tmp_path))
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        payload = {"query": "标题", "job_ids": ["a" * 32]}
        assert (await client.post("/api/material-search", json=payload,
            headers={"Origin": "https://external.example"})).status_code == 403
        app.state.legacy_main_port = 18765
        # Native job avoids making an actual loopback request in this test.
        app.state.container.job_service.repository.add(completed_video_job("a" * 32))
        assert (await client.post("/api/material-search", json=payload,
            headers={"Origin": "http://127.0.0.1:18765"})).status_code == 200
        assert (await client.post("/api/material-search", json={**payload, "job_ids": ["../private"]})).status_code == 422
        assert (await client.post("/api/material-search", json={**payload, "query": "x" * 501})).status_code == 422
