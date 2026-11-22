from concurrent.futures import ThreadPoolExecutor

from httpx import ASGITransport, AsyncClient

from voxpull.app import create_app
from voxpull.infrastructure.material_tags import MaterialTagStore
from test_api import make_settings


async def test_material_tags_survive_restart_without_changing_jobs(tmp_path):
    settings = make_settings(tmp_path)
    app = create_app(settings)
    ident = "a" * 32  # Tags also support tasks still held by the legacy main service.
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        assert (await client.get("/api/material-tags")).json() == {"tags": [], "assignments": {}}
        first = (await client.post("/api/material-tags", json={"name": "  AI   学习  "})).json()
        duplicate = (await client.post("/api/material-tags", json={"name": "ai 学习"})).json()
        assert duplicate == first
        other = (await client.post("/api/material-tags", json={"name": "投资"})).json()
        assert (await client.post(f"/api/material-tags/{ident}", json={"tag_ids": [first["id"], other["id"]]})).status_code == 422
        response = await client.post(f"/api/material-tags/{ident}", json={"tag_ids": [first["id"]]})
        assert response.json()["tag_ids"] == [first["id"]]
        response = await client.post(f"/api/material-tags/{ident}", json={"tag_ids": [other["id"]]})
        assert response.status_code == 200
        assert response.json()["tag_ids"] == [other["id"]]
        before = (await client.get("/api/material-tags")).json()
        assert (await client.post(f"/api/material-tags/{ident}", json={"tag_ids": ["missing"]})).status_code == 422
        assert (await client.get("/api/material-tags")).json() == before
    restarted = create_app(settings)
    async with AsyncClient(transport=ASGITransport(restarted), base_url="http://test") as client:
        assert (await client.get("/api/material-tags")).json() == before
        assert (await client.post(f"/api/material-tags/{ident}", json={"tag_ids": []})).status_code == 200
        assert (await client.get("/api/material-tags")).json()["assignments"] == {}
    assert not list((settings.data_dir / "task-records").glob("job-*.json"))


async def test_material_tag_validation_and_local_origin(tmp_path):
    app = create_app(make_settings(tmp_path))
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        for name in ["", "  ", "长" * 41]:
            assert (await client.post("/api/material-tags", json={"name": name})).status_code == 422
        assert (await client.post("/api/material-tags/not-a-job", json={"tag_ids": []})).status_code == 422
        assert (await client.post("/api/material-tags", json={"name": "test"}, headers={"Origin": "https://external.example"})).status_code == 403
        app.state.legacy_main_port = 18765
        assert (await client.post("/api/material-tags", json={"name": "test"}, headers={"Origin": "http://127.0.0.1:18765"})).status_code == 200


def test_parallel_tag_writes_do_not_lose_labels_or_assignments(tmp_path):
    path = tmp_path / "tags.json"

    def add(index):
        store = MaterialTagStore(path)
        tag = store.create(f"标签 {index}")
        store.assign(f"{index:032x}", [tag["id"]])

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(add, range(24)))
    data = MaterialTagStore(path).read()
    assert len(data["tags"]) == len(data["assignments"]) == 24
    assert path.stat().st_mode & 0o777 == 0o600


async def test_bulk_tags_are_atomic_and_reconfirm_if_labels_change(tmp_path):
    app = create_app(make_settings(tmp_path))
    a, b, untouched = "a" * 32, "b" * 32, "c" * 32
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        tags = [(await client.post("/api/material-tags", json={"name": name})).json()["id"] for name in ("旧标签", "新标签", "其他标签")]
        await client.post("/api/material-tags/bulk", json={"job_ids": [a, untouched], "tag_id": tags[0]})
        payload = {"job_ids": [a, b, a], "tag_id": tags[1]}
        before = (await client.get("/api/material-tags")).json()
        response = await client.post("/api/material-tags/bulk", json=payload)
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["conflicts"] == [{"job_id": a, "tag_ids": [tags[0]], "tag_names": ["旧标签"]}]
        assert detail["expected_assignments"] == {a: [tags[0]], b: []}
        assert (await client.get("/api/material-tags")).json() == before
        # Another window changes a label between preview and confirmation.
        store = MaterialTagStore(app.state.container.settings.data_dir / "material-tags.json")
        store.assign(a, [tags[2]], overwrite=True, expected_assignments={a: [tags[0]]})
        payload.update(overwrite=True, expected_assignments=detail["expected_assignments"])
        response = await client.post("/api/material-tags/bulk", json=payload)
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["code"] == "tag_assignment_changed"
        data = (await client.get("/api/material-tags")).json()
        assert b not in data["assignments"]
        assert data["assignments"][a] == [tags[2]]
        payload["expected_assignments"] = detail["expected_assignments"]
        response = await client.post("/api/material-tags/bulk", json=payload)
        assert response.status_code == 200 and response.json()["updated"] == 2
        data = (await client.get("/api/material-tags")).json()
        assert data["assignments"] == {a: [tags[1]], b: [tags[1]], untouched: [tags[0]]}
        # Reapplying the same label is harmless and does not prompt.
        response = await client.post("/api/material-tags/bulk", json={"job_ids": [a, b], "tag_id": tags[1]})
        assert response.status_code == 200
        assert (await client.post("/api/material-tags/bulk", json={"job_ids": [a, "invalid"], "tag_id": tags[0]})).status_code == 422
        assert (await client.get("/api/material-tags")).json() == data
        # Clearing multiple labels uses the same all-or-nothing confirmation.
        payload = {"job_ids": [a, b, untouched], "tag_id": None}
        response = await client.post("/api/material-tags/bulk", json=payload)
        assert response.status_code == 409
        assert (await client.get("/api/material-tags")).json() == data
        payload.update(overwrite=True, expected_assignments=response.json()["detail"]["expected_assignments"])
        response = await client.post("/api/material-tags/bulk", json=payload)
        assert response.status_code == 200
        assert response.json()["assignments"] == {a: [], b: [], untouched: []}
        after = (await client.get("/api/material-tags")).json()
        assert after["assignments"] == {} and after["tags"] == data["tags"]


async def test_legacy_multiple_labels_are_only_replaced_after_confirmation(tmp_path):
    import json
    settings = make_settings(tmp_path)
    app = create_app(settings)
    path = settings.data_dir / "material-tags.json"
    ident = "a" * 32
    path.write_text(json.dumps({"tags": [{"id": "old1", "name": "旧一"}, {"id": "old2", "name": "旧二"}],
                                "assignments": {ident: ["old1", "old2"]}}))
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.post("/api/material-tags/bulk", json={"job_ids": [ident, "b" * 32], "tag_id": "old1"})
        assert response.status_code == 409
        assert json.loads(path.read_text())["assignments"][ident] == ["old1", "old2"]
        response = await client.post("/api/material-tags/bulk", json={"job_ids": [ident, "b" * 32], "tag_id": "old1", "overwrite": True,
            "expected_assignments": response.json()["detail"]["expected_assignments"]})
        assert response.json()["assignments"] == {ident: ["old1"], "b" * 32: ["old1"]}


async def test_bulk_endpoint_with_one_distinct_material_edits_without_confirmation(tmp_path):
    app = create_app(make_settings(tmp_path))
    ident = "a" * 32
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        old, new = [(await client.post("/api/material-tags", json={"name": name})).json()["id"] for name in ("旧", "新")]
        await client.post("/api/material-tags/bulk", json={"job_ids": [ident], "tag_id": old})
        response = await client.post("/api/material-tags/bulk", json={"job_ids": [ident, ident], "tag_id": new})
        assert response.status_code == 200
        assert response.json() == {"updated": 1, "assignments": {ident: [new]}}
        response = await client.post("/api/material-tags/bulk", json={"job_ids": [ident], "tag_id": None})
        assert response.status_code == 200 and response.json()["assignments"][ident] == []


async def test_delete_unused_tag_and_confirm_used_tag_without_deleting_materials(tmp_path):
    settings = make_settings(tmp_path)
    app = create_app(settings)
    material = tmp_path / "keep.mp4"
    material.write_bytes(b"keep original material")
    stamp = material.stat().st_mtime_ns
    a, b, other = "a" * 32, "b" * 32, "c" * 32
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        empty, used, kept = [(await client.post("/api/material-tags", json={"name": name})).json()["id"] for name in ("空标签", "使用中", "其他")]
        await client.post("/api/material-tags/bulk", json={"job_ids": [a, b], "tag_id": used})
        await client.post("/api/material-tags/bulk", json={"job_ids": [other], "tag_id": kept})
        response = await client.post(f"/api/material-tags/{empty}/delete", json={})
        assert response.status_code == 200 and response.json()["cleared_count"] == 0
        before = (await client.get("/api/material-tags")).json()
        response = await client.post(f"/api/material-tags/{used}/delete", json={})
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["count"] == 2 and detail["expected_job_ids"] == [a, b]
        assert (await client.get("/api/material-tags")).json() == before
        response = await client.post(f"/api/material-tags/{used}/delete", json={"confirm": True, "expected_job_ids": detail["expected_job_ids"]})
        assert response.status_code == 200 and response.json()["cleared_count"] == 2
        data = (await client.get("/api/material-tags")).json()
        assert data["assignments"] == {other: [kept]} and [tag["id"] for tag in data["tags"]] == [kept]
        assert (await client.post(f"/api/material-tags/{used}/delete", json={})).status_code == 404
        assert (await client.post(f"/api/material-tags/{kept}/delete", json={}, headers={"Origin": "https://external.example"})).status_code == 403
        assert (await client.get("/api/material-tags")).json() == data
    assert material.read_bytes() == b"keep original material" and material.stat().st_mtime_ns == stamp


async def test_tag_delete_reconfirms_reference_changes_and_preserves_other_legacy_tags(tmp_path):
    import json
    settings = make_settings(tmp_path)
    app = create_app(settings)
    a, hidden = "a" * 32, "d" * 32
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        used, other = [(await client.post("/api/material-tags", json={"name": name})).json()["id"] for name in ("删除", "保留")]
        await client.post("/api/material-tags/bulk", json={"job_ids": [a], "tag_id": used})
        preview = (await client.post(f"/api/material-tags/{used}/delete", json={})).json()["detail"]
        # References outside any current task list must also be checked.
        path = settings.data_dir / "material-tags.json"
        data = json.loads(path.read_text())
        data["assignments"][a] = [used, other]
        data["assignments"][hidden] = [used]
        path.write_text(json.dumps(data))
        before = path.read_text()
        response = await client.post(f"/api/material-tags/{used}/delete", json={"confirm": True, "expected_job_ids": preview["expected_job_ids"]})
        assert response.status_code == 409 and response.json()["detail"]["code"] == "tag_delete_changed"
        assert path.read_text() == before
        detail = response.json()["detail"]
        assert detail["count"] == 2 and detail["expected_job_ids"] == [a, hidden]
        response = await client.post(f"/api/material-tags/{used}/delete", json={"confirm": True, "expected_job_ids": detail["expected_job_ids"]})
        assert response.status_code == 200 and response.json()["assignments"] == {a: [other]}
