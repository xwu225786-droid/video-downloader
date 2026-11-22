import copy
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from voxpull.domain.naming import compact_media_id
from voxpull.infrastructure.material_folders import ensure_material_folder, folder_title, find_material_folder
from voxpull.infrastructure.material_reorganization import (
    apply_reorganization, digest, plan_reorganization, rollback_reorganization, plan_friendly_names,
)
from voxpull.infrastructure.storage import LocalStorage


def test_title_folders_are_safe_stable_and_do_not_overwrite_same_titles(tmp_path):
    root = tmp_path / "videos"
    root.mkdir()
    (root / "同名作品").mkdir()
    (root / "同名作品" / "用户文件.txt").write_text("保留")
    with ThreadPoolExecutor(max_workers=8) as pool:
        folders = list(pool.map(lambda i: ensure_material_folder(root, str(i % 4), "同名作品"), range(24)))
    assert len(set(folders)) == 4
    assert all(p.parent == root and p.name != "同名作品" for p in folders)
    assert (root / "同名作品" / "用户文件.txt").read_text() == "保留"
    assert ensure_material_folder(root, "1", "后续变更标题") == folders[1]
    title = folder_title('../危险\\标题:\n' + '长' * 200, 'id')
    assert '/' not in title and '\\' not in title and '\n' not in title
    assert len(title.encode()) <= 180 and title not in ['.', '..']


def test_saved_video_cover_title_and_text_share_one_title_folder_after_restart(tmp_path):
    storage = LocalStorage(tmp_path / "work", tmp_path / "videos")
    folder = storage.prepare_material("123", "作品标题", "video")
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    cover = tmp_path / "cover.jpg"
    cover.write_bytes(b"cover")
    video = storage.publish_video(source, "123")
    saved_cover, _ = storage.publish_video_details(cover, "作品标题", "123")
    title, text = storage.save_material_text("123", "作品标题", "video", description="作品正文", transcript="逐字稿")
    assert {p.parent for p in [video, saved_cover, title, text]} == {folder}
    assert folder.name == "作品标题"
    assert text.read_text() == "逐字稿" and (folder / "作品文案.txt").read_text() == "作品正文"
    restarted = LocalStorage(tmp_path / "work", tmp_path / "videos")
    assert restarted.find_video("123") == video


def library(tmp_path):
    videos, images = tmp_path / "videos", tmp_path / "images"
    videos.mkdir()
    images.mkdir()
    jobs = {}
    for ident in ['123', '456']:
        stem = compact_media_id(ident)
        (videos / f"{stem}.mp4").write_bytes(ident.encode())
        (videos / f"{stem}.cover.jpg").write_bytes(b"cover")
        (videos / f"{stem}.title.txt").write_text("同名作品")
        jobs[ident] = {'id': ident, 'created_at': ident, 'status': 'completed', 'metadata': {}, 'result': {
            'media': {'id': ident, 'kind': 'video', 'title': '同名作品', 'filename': f'{stem}.mp4',
                      'absolute_path': str(videos / f'{stem}.mp4'), 'saved': True,
                      'cover_path': str(videos / f'{stem}.cover.jpg'), 'title_path': str(videos / f'{stem}.title.txt')},
            'transcript': {'text': '原始逐字稿 '+ident}}}
    gallery = images / 'old-id'
    gallery.mkdir()
    (gallery / '001.png').write_bytes(b'image')
    (gallery / '001.live.mp4').write_bytes(b'live')
    (gallery / 'manifest.json').write_text(json.dumps({'id': 'gallery', 'title': '图文标题', 'description': '原始图文正文'}))
    jobs['gallery'] = {'id': 'gallery', 'created_at': 'now', 'metadata': {}, 'result': {'transcript': None, 'media': {
        'id': 'gallery', 'kind': 'images', 'title': '图文标题', 'description': '原始图文正文',
        'filename': gallery.name, 'absolute_path': str(gallery), 'saved': True,
        'assets': [{'absolute_path': str(gallery / '001.png'), 'filename': '001.png'}]}}}
    return videos, images, jobs


def test_migration_keeps_bytes_updates_paths_persists_text_and_can_roll_back(tmp_path):
    videos, images, jobs = library(tmp_path)
    original = copy.deepcopy(jobs)
    before = {str(p): digest(p) for root in [videos, images] for p in root.rglob('*') if p.is_file()}
    plan = plan_reorganization(videos, images, jobs)
    assert jobs == original and len(plan['groups']) == 3
    assert len({g['target'] for g in plan['groups']}) == 3
    journal = tmp_path / 'journal.json'
    apply_reorganization(plan, journal)
    assert not list(videos.glob('*.mp4'))
    for ident in ['123', '456']:
        media = plan['jobs'][ident]['result']['media']
        video = Path(media['absolute_path'])
        assert video.read_bytes() == ident.encode()
        assert Path(media['description_path']).read_text() == '原始逐字稿 '+ident
        assert {Path(media[k]).parent for k in ['cover_path', 'title_path', 'description_path']} == {video.parent}
        assert find_material_folder(videos, ident) == video.parent
    media = plan['jobs']['gallery']['result']['media']
    folder = Path(media['absolute_path'])
    assert folder.name == '图文标题' and Path(media['assets'][0]['absolute_path']).read_bytes() == b'image'
    assert (folder/'文案.txt').read_text() == '原始图文正文'
    assert (folder/'标题.txt').read_text() == '图文标题'
    second = plan_reorganization(videos, images, plan['jobs'])
    assert not second['moves'] and not second['writes']
    rollback_reorganization(journal)
    assert {str(p): digest(p) for root in [videos, images] for p in root.rglob('*') if p.is_file()} == before


def test_migration_rejects_changed_files_before_mutation(tmp_path):
    videos, images, jobs = library(tmp_path)
    plan = plan_reorganization(videos, images, jobs)
    path = next(videos.glob('*.mp4'))
    path.write_bytes(b'changed')
    before = {str(p): p.read_bytes() for root in [videos, images] for p in root.rglob('*') if p.is_file()}
    with pytest.raises(ValueError, match='发生变化'):
        apply_reorganization(plan, tmp_path/'journal.json')
    assert before == {str(p): p.read_bytes() for root in [videos, images] for p in root.rglob('*') if p.is_file()}


def test_migration_rolls_back_when_a_move_fails(tmp_path, monkeypatch):
    import voxpull.infrastructure.material_reorganization as module
    videos, images, jobs = library(tmp_path)
    before = {str(p): p.read_bytes() for root in [videos, images] for p in root.rglob('*') if p.is_file()}
    plan = plan_reorganization(videos, images, jobs)
    rename, calls = module.os.rename, []
    def fail_once(old, new):
        calls.append(old)
        if len(calls) == 3:
            raise OSError('simulated interruption')
        return rename(old, new)
    monkeypatch.setattr(module.os, 'rename', fail_once)
    with pytest.raises(OSError, match='interruption'):
        apply_reorganization(plan, tmp_path/'journal.json')
    assert before == {str(p): p.read_bytes() for root in [videos, images] for p in root.rglob('*') if p.is_file()}


def test_friendly_names_keep_media_bytes_assets_and_support_rollback(tmp_path):
    videos, images, jobs = library(tmp_path)
    first = plan_reorganization(videos, images, jobs)
    apply_reorganization(first, tmp_path / "first.json")
    before = {str(p): p.read_bytes() for root in [videos, images] for p in root.rglob("*") if p.is_file()}
    names = plan_friendly_names(videos, images, first["jobs"])
    apply_reorganization(names, tmp_path / "names.json")
    for ident in ["123", "456"]:
        media = names["jobs"][ident]["result"]["media"]
        assert media["filename"] == "视频.mp4"
        video = Path(media["absolute_path"])
        assert video.name == "视频.mp4" and video.read_bytes() == ident.encode()
        assert Path(media["cover_path"]).name == "封面.jpg"
        assert Path(media["title_path"]).name == "标题.txt"
        assert Path(media["description_path"]).name == "文案.txt"
        assert LocalStorage(tmp_path / "work", videos, images).find_video(ident) == video
    media = names["jobs"]["gallery"]["result"]["media"]
    folder = Path(media["absolute_path"])
    assert Path(media["assets"][0]["absolute_path"]).name == "图片1.png"
    assert media["assets"][0]["filename"] == "图片1.png"
    assert (folder / "视频1.mp4").read_bytes() == b"live"
    assert Path(media["cover_path"]).read_bytes() == (folder / "图片1.png").read_bytes() == b"image"
    again = plan_friendly_names(videos, images, names["jobs"])
    assert not again["moves"] and not again["copies"] and not again["edits"]
    rollback_reorganization(tmp_path / "names.json")
    assert {str(p): p.read_bytes() for root in [videos, images] for p in root.rglob("*") if p.is_file()} == before
