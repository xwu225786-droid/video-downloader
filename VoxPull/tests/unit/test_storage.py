from __future__ import annotations

import json
from pathlib import Path

from voxpull.infrastructure.storage import LocalStorage


def test_media_root_update_is_persisted_and_restored(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    location_path = data_root / "storage-location.json"
    selected_root = tmp_path / "Media Library"
    selected_root.mkdir()

    storage = LocalStorage(
        data_root / "work",
        data_root / "videos",
        data_root / "images",
        location_path,
    )
    storage.update_media_root(selected_root)

    assert storage.work_root == selected_root / "work"
    assert storage.media_root == selected_root.resolve()
    assert storage.videos_root == selected_root / "videos"
    assert storage.images_root == selected_root / "images"
    assert storage.work_root.is_dir()
    assert storage.videos_root.is_dir()
    assert storage.images_root.is_dir()
    work_dir = storage.create_work_dir("new-location-job")
    assert work_dir.parent == selected_root / "work"
    assert json.loads(location_path.read_text(encoding="utf-8")) == {
        "media_root": str(selected_root.resolve())
    }
    assert location_path.stat().st_mode & 0o777 == 0o600

    restored = LocalStorage(
        data_root / "work",
        data_root / "videos",
        data_root / "images",
        location_path,
    )
    assert restored.work_root == selected_root / "work"
    assert restored.media_root == selected_root.resolve()
    assert restored.videos_root == selected_root / "videos"
    assert restored.images_root == selected_root / "images"


def test_invalid_persisted_media_root_falls_back_to_data_directory(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    location_path = data_root / "storage-location.json"
    location_path.write_text(
        json.dumps({"media_root": str(tmp_path / "missing")}) + "\n",
        encoding="utf-8",
    )

    storage = LocalStorage(
        data_root / "work",
        data_root / "videos",
        data_root / "images",
        location_path,
    )

    assert storage.work_root == data_root / "work"
    assert storage.media_root == data_root
    assert storage.videos_root == data_root / "videos"
    assert storage.images_root == data_root / "images"


def test_video_uses_stable_ten_character_name(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    storage = LocalStorage(data_root / "work", data_root / "videos")
    source = tmp_path / "downloaded.mp4"
    source.write_bytes(b"video")

    published = storage.publish_video(source, "7587447081268047268")

    assert published.suffix == ".mp4"
    assert len(published.stem) == 10
    assert published.stem.isalnum()
    assert storage.find_video("7587447081268047268") == published


def test_existing_long_video_is_migrated_to_ten_character_name(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    storage = LocalStorage(data_root / "work", data_root / "videos")
    media_id = "7587447081268047268"
    legacy_video = storage.videos_root / f"{media_id}.mp4"
    legacy_video.write_bytes(b"video")

    found = storage.find_video(media_id)

    assert found is not None
    assert len(found.stem) == 10
    assert found != legacy_video
    assert found.read_bytes() == b"video"
    assert not legacy_video.exists()


def test_image_folder_uses_stable_ten_character_name(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    storage = LocalStorage(data_root / "work", data_root / "videos", data_root / "images")
    source = tmp_path / "gallery"
    source.mkdir()
    (source / "001.jpg").write_bytes(b"image")

    published = storage.publish_image_folder(source, "7587447081268047268")

    assert len(published.name) == 10
    assert published.name.isalnum()
    assert storage.find_image_folder("7587447081268047268") == published


def test_existing_long_image_folder_is_migrated_to_ten_character_name(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    storage = LocalStorage(data_root / "work", data_root / "videos", data_root / "images")
    media_id = "7587447081268047268"
    legacy_folder = storage.images_root / media_id
    legacy_folder.mkdir()
    (legacy_folder / "001.jpg").write_bytes(b"image")

    found = storage.find_image_folder(media_id)

    assert found is not None
    assert len(found.name) == 10
    assert found != legacy_folder
    assert (found / "001.jpg").read_bytes() == b"image"
    assert not legacy_folder.exists()


def test_manifest_and_live_motion_do_not_make_a_gallery_reusable(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    storage = LocalStorage(data_root / "work", data_root / "videos", data_root / "images")
    media_id = "7587447081268047268"
    legacy_folder = storage.images_root / media_id
    legacy_folder.mkdir()
    (legacy_folder / "manifest.json").write_text("{}", encoding="utf-8")
    (legacy_folder / "001.live.mp4").write_bytes(b"motion")
    (legacy_folder / ".001.part").write_bytes(b"partial")

    assert storage.find_image_folder(media_id) is None


def test_image_source_policy_invalidates_a_legacy_gallery(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    storage = LocalStorage(data_root / "work", data_root / "videos", data_root / "images")
    media_id = "69a6b5b0000000000d009fe8"
    folder = storage.images_root / media_id
    folder.mkdir()
    (folder / "001.jpg").write_bytes(b"watermarked")
    (folder / "manifest.json").write_text("{}", encoding="utf-8")

    assert (
        storage.find_image_folder(
            media_id,
            source_policy="xiaohongshu-original-png-v3",
        )
        is None
    )


def test_image_source_policy_reuses_a_matching_gallery(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    storage = LocalStorage(data_root / "work", data_root / "videos", data_root / "images")
    media_id = "69a6b5b0000000000d009fe8"
    folder = storage.images_root / media_id
    folder.mkdir()
    (folder / "001.png").write_bytes(b"original")
    (folder / "manifest.json").write_text(
        json.dumps({"image_source_policy": "xiaohongshu-original-png-v3"}),
        encoding="utf-8",
    )

    found = storage.find_image_folder(
        media_id,
        source_policy="xiaohongshu-original-png-v3",
    )

    assert found is not None
    assert found.name != media_id
    assert (found / "001.png").read_bytes() == b"original"
