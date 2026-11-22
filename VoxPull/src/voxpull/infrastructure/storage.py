from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
from pathlib import Path

from voxpull.domain.naming import compact_media_id, safe_media_id
from voxpull.infrastructure.material_folders import ensure_material_folder, find_material_folder


logger = logging.getLogger(__name__)
_IMAGE_EXTENSIONS = {".avif", ".gif", ".heic", ".heif", ".jpeg", ".jpg", ".png", ".webp"}


class LocalStorage:
    def __init__(
        self,
        work_root: Path,
        videos_root: Path,
        images_root: Path | None = None,
        location_path: Path | None = None,
    ) -> None:
        self.location_path = location_path
        self._location_lock = threading.RLock()
        default_images_root = images_root or videos_root.parent / "images"
        media_root = _load_media_root(location_path)
        if media_root is not None:
            work_root = media_root / "work"
            videos_root = media_root / "videos"
            default_images_root = media_root / "images"
        self._work_root = work_root
        self._media_root = videos_root.parent
        self._videos_root = videos_root
        self._images_root = default_images_root
        self._ensure_media_directories()

    @property
    def work_root(self) -> Path:
        with self._location_lock:
            return self._work_root

    @property
    def media_root(self) -> Path:
        with self._location_lock:
            return self._media_root

    @property
    def videos_root(self) -> Path:
        with self._location_lock:
            return self._videos_root

    @property
    def images_root(self) -> Path:
        with self._location_lock:
            return self._images_root

    def update_media_root(self, media_root: Path) -> None:
        resolved_root = media_root.expanduser().resolve()
        work_root = resolved_root / "work"
        videos_root = resolved_root / "videos"
        images_root = resolved_root / "images"
        with self._location_lock:
            work_root.mkdir(parents=True, exist_ok=True)
            videos_root.mkdir(parents=True, exist_ok=True)
            images_root.mkdir(parents=True, exist_ok=True)
            _verify_writable(work_root)
            _verify_writable(videos_root)
            _verify_writable(images_root)
            if self.location_path is not None:
                _write_media_root(self.location_path, resolved_root)
            self._work_root = work_root
            self._media_root = resolved_root
            self._videos_root = videos_root
            self._images_root = images_root

    def _ensure_media_directories(self) -> None:
        try:
            self._work_root.mkdir(parents=True, exist_ok=True)
            self._videos_root.mkdir(parents=True, exist_ok=True)
            self._images_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            if self.location_path is None:
                raise
            logger.warning(
                "Configured media directory is unavailable; falling back to the data directory",
                exc_info=True,
            )
            default_root = self.location_path.parent
            self._work_root = default_root / "work"
            self._media_root = default_root
            self._videos_root = default_root / "videos"
            self._images_root = default_root / "images"
            self._work_root.mkdir(parents=True, exist_ok=True)
            self._videos_root.mkdir(parents=True, exist_ok=True)
            self._images_root.mkdir(parents=True, exist_ok=True)

    def create_work_dir(self, job_id: str) -> Path:
        path = self.work_root / job_id
        path.mkdir(parents=True, exist_ok=False)
        return path

    def prepare_material(self, media_id: str, title: str, kind: str) -> Path:
        root = self.images_root if kind == "images" else self.videos_root
        return ensure_material_folder(root, media_id, title)

    def save_material_text(
        self, media_id: str, title: str, kind: str, *,
        description: str = "", transcript: str | None = None,
    ) -> tuple[Path, Path | None]:
        folder = self.prepare_material(media_id, title, kind)
        title_path = folder / "标题.txt"
        _write_text(title_path, title)
        text_path = None
        if description:
            text_path = folder / ("文案.txt" if kind == "images" else "作品文案.txt")
            _write_text(text_path, description)
        if transcript is not None:
            text_path = folder / "文案.txt"
            _write_text(text_path, transcript)
        return title_path, text_path

    def find_video(self, video_id: str) -> Path | None:
        folder = find_material_folder(self.videos_root, video_id)
        path = folder / "视频.mp4" if folder else self.videos_root / f"{compact_media_id(video_id)}.mp4"
        if _has_video(path):
            return path

        previous = folder / f"{compact_media_id(video_id)}.mp4" if folder else None
        if previous and _has_video(previous):
            os.replace(previous, path)
            return path
        flat_path = self.videos_root / f"{compact_media_id(video_id)}.mp4"
        if folder and _has_video(flat_path):
            os.replace(flat_path, path)
            return path
        # Keep videos saved by versions that used the full media ID reusable.
        legacy_path = self.videos_root / f"{safe_media_id(video_id)}.mp4"
        if not _has_video(legacy_path):
            return None
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        os.replace(legacy_path, path)
        return path

    def publish_video(self, source: Path, video_id: str) -> Path:
        folder = find_material_folder(self.videos_root, video_id)
        destination = folder / "视频.mp4" if folder else self.videos_root / f"{compact_media_id(video_id)}.mp4"
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, destination)
        return destination

    def publish_video_details(
        self, cover: Path, title: str, video_id: str
    ) -> tuple[Path, Path]:
        # Keep these files even when the user discards the temporary MP4.
        root = find_material_folder(self.videos_root, video_id) or self.videos_root
        root.mkdir(parents=True, exist_ok=True)
        stem = compact_media_id(video_id)
        named = root != self.videos_root
        cover_path = root / ("封面.jpg" if named else f"{stem}.cover.jpg")
        title_path = root / ("标题.txt" if named else f"{stem}.title.txt")
        title_tmp = cover.parent / "title.txt"
        title_tmp.write_text(title, encoding="utf-8")
        os.replace(cover, cover_path)
        os.replace(title_tmp, title_path)
        return cover_path, title_path

    def find_image_folder(
        self,
        media_id: str,
        *,
        source_policy: str | None = None,
    ) -> Path | None:
        folder = find_material_folder(self.images_root, media_id)
        path = folder or self.images_root / _image_folder_name(media_id)
        if _has_images(path, source_policy=source_policy):
            return path

        flat_path = self.images_root / _image_folder_name(media_id)
        if folder and _has_images(flat_path, source_policy=source_policy):
            if path.exists():
                path.rmdir()  # Only replace the empty directory reserved by prepare_material.
            os.replace(flat_path, path)
            return path
        # Keep previously downloaded galleries reusable after switching from
        # full media IDs to compact folder names.
        legacy_path = self.images_root / safe_media_id(media_id)
        if not _has_images(legacy_path, source_policy=source_policy):
            return None
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        os.replace(legacy_path, path)
        return path

    def publish_image_folder(self, source: Path, media_id: str) -> Path:
        destination = find_material_folder(self.images_root, media_id) or self.images_root / _image_folder_name(media_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            shutil.rmtree(destination)
        os.replace(source, destination)
        return destination

    def name_gallery_files(self, folder: Path) -> Path | None:
        import re
        renamed = {}
        for source in sorted(folder.iterdir()):
            match = re.fullmatch(r"(\d+)(\.live)?(\.[^.]+)", source.name)
            if not source.is_file() or not match:
                continue
            label = "视频" if match[2] else "图片"
            target = folder / f"{label}{int(match[1])}{match[3]}"
            if target.exists():
                raise FileExistsError("图集目标文件已存在，未覆盖")
            source.rename(target)
            renamed[source.name] = target.name
        manifest_path = folder / "manifest.json"
        if renamed and manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for asset in manifest.get("assets", []):
                for key in ("image", "motion"):
                    if asset.get(key) in renamed:
                        asset[key] = renamed[asset[key]]
            _write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        images = sorted((p for p in folder.iterdir() if re.fullmatch(r"图片\d+\.[^.]+", p.name)),
                        key=lambda p: int(re.search(r"\d+", p.name)[0]))
        if not images:
            return None
        cover = folder / ("封面" + images[0].suffix)
        if not cover.exists():
            shutil.copy2(images[0], cover)
        return cover

    def cleanup_work_dir(self, job_id: str) -> None:
        shutil.rmtree(self.work_root / job_id, ignore_errors=True)

    def cleanup_stale_work_dirs(self, max_age_hours: int = 24) -> int:
        cutoff = time.time() - max_age_hours * 3600
        removed = 0
        for path in self.work_root.iterdir():
            if path.is_dir() and path.stat().st_mtime < cutoff:
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
        return removed


def _image_folder_name(media_id: str) -> str:
    return compact_media_id(media_id)


def _has_video(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def _has_images(path: Path, *, source_policy: str | None = None) -> bool:
    has_image = path.is_dir() and any(
        item.is_file()
        and not item.name.startswith(".")
        and item.stem != "封面"
        and item.suffix.lower() in _IMAGE_EXTENSIONS
        and item.stat().st_size > 0
        for item in path.iterdir()
    )
    if not has_image or source_policy is None:
        return has_image
    try:
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return isinstance(manifest, dict) and manifest.get("image_source_policy") == source_policy


def _load_media_root(location_path: Path | None) -> Path | None:
    if location_path is None or not location_path.is_file():
        return None
    try:
        payload = json.loads(location_path.read_text(encoding="utf-8"))
        value = payload.get("media_root")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("media_root is missing")
        media_root = Path(value).expanduser().resolve()
        if not media_root.is_dir():
            raise ValueError("media_root is unavailable")
        return media_root
    except (OSError, ValueError, json.JSONDecodeError):
        logger.warning("Ignoring invalid storage location file: %s", location_path, exc_info=True)
        return None


def _write_media_root(location_path: Path, media_root: Path) -> None:
    location_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = location_path.with_suffix(f"{location_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps({"media_root": str(media_root)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.chmod(0o600)
    os.replace(temporary_path, location_path)
    location_path.chmod(0o600)


def _verify_writable(directory: Path) -> None:
    probe = directory / f".voxpull-write-check-{os.getpid()}-{threading.get_ident()}"
    try:
        descriptor = os.open(probe, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
    finally:
        probe.unlink(missing_ok=True)


def _write_text(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
