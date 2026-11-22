import asyncio
import logging
from pathlib import Path

import pytest

from voxpull.application.job_service import InMemoryJobRepository
from voxpull.application.pipeline import TranscriptionPipeline
from voxpull.domain.errors import DownloadFailedError, TranscriptionFailedError
from voxpull.domain.models import (
    BrowserEvidence,
    DOUYIN_PUBLIC_SHARE_POLICY,
    DOUYIN_GUEST_POLICY,
    Job,
    JobStatus,
    ImageAssetMetadata,
    MediaKind,
    MediaMetadata,
    Transcript,
    TranscriptSegment,
)
from voxpull.infrastructure.storage import LocalStorage


class FakeBrowser:
    async def acquire(self, url: str, cookie_file: Path, *, on_state=None) -> BrowserEvidence:
        cookie_file.write_text("# Netscape HTTP Cookie File\n")
        return BrowserEvidence("https://www.douyin.com/video/123", "fake-agent", cookie_file)


class FakeDownloader:
    downloads = 0

    async def probe(self, url: str, cookie_file: Path, user_agent: str) -> MediaMetadata:
        return MediaMetadata("123", "测试视频", duration=5.0)

    async def download(self, url, metadata, cookie_file, user_agent, work_dir, progress) -> Path:
        self.downloads += 1
        progress(50, "下载中")
        output = work_dir / "123.mp4"
        output.write_bytes(b"fake mp4")
        return output

    async def download_images(
        self, url, metadata, cookie_file, user_agent, work_dir, progress
    ) -> Path:
        raise AssertionError("video test must not download images")


class BrowserMetadataDownloader(FakeDownloader):
    async def probe(self, url: str, cookie_file: Path, user_agent: str) -> MediaMetadata:
        raise AssertionError("browser metadata should bypass yt-dlp probing")


class FakeAudioExtractor:
    async def extract(self, video_path: Path, audio_path: Path) -> None:
        assert video_path.is_file()
        audio_path.write_bytes(b"fake wav")


class FakeCoverExtractor:
    async def extract(self, video_path: Path, cover_path: Path) -> None:
        assert video_path.is_file()
        cover_path.write_bytes(b"test cover jpeg")


@pytest.mark.parametrize("save_video", [False, True])
@pytest.mark.parametrize("policy", [DOUYIN_PUBLIC_SHARE_POLICY, DOUYIN_GUEST_POLICY])
async def test_public_copy_runs_through_transcription_with_separate_storage(tmp_path, save_video, policy):
    class PublicShareBrowser:
        async def acquire(self, url, cookie_file, *, on_state=None):
            copy = cookie_file.with_name("share.mp4")
            copy.write_bytes(b"share copy")
            return BrowserEvidence(url, "test-agent", cookie_file,
                                   MediaMetadata("123", "测试视频", video_source_policy=policy), copy)

    class AlreadyDownloaded(BrowserMetadataDownloader):
        async def download(self, *args):
            raise AssertionError("the fallback copy was already downloaded")

    repository = InMemoryJobRepository()
    url = "https://www.douyin.com/video/123"
    repository.add(Job("share", url, "zh", save_video=save_video))
    storage = LocalStorage(tmp_path / "work", tmp_path / "videos")
    original_id = "123_douyin-guest-v1" if policy == DOUYIN_GUEST_POLICY else "123_douyin-internal-v1"
    internal_dir = storage.prepare_material(original_id, "测试视频", "video")
    internal = internal_dir / "视频.mp4"
    internal.write_bytes(b"original")
    pipeline = TranscriptionPipeline(repository, PublicShareBrowser(), AlreadyDownloaded(),
                                     FakeAudioExtractor(), FakeTranscriber(), storage)

    await pipeline.execute("share")

    job = repository.get("share")
    assert job.status is JobStatus.COMPLETED and job.result.transcript is not None
    assert ("访客公开资源" if policy == DOUYIN_GUEST_POLICY else "公开分享页水印版") in job.message
    assert job.result.media.video_source_policy == policy
    path = Path(job.result.media.absolute_path)
    assert path != internal and internal.read_bytes() == b"original"
    assert path.exists() == save_video
    if save_video:
        assert path.read_bytes() == b"share copy"


@pytest.mark.parametrize("save_video", [False, True])
async def test_video_cover_and_title_survive_work_cleanup_and_storage_change(
    tmp_path: Path, save_video: bool
) -> None:
    repository = InMemoryJobRepository()
    repository.add(Job("details", "https://v.douyin.com/test/", "zh", save_video=save_video))
    storage = LocalStorage(tmp_path / "work", tmp_path / "videos")
    chosen_root = tmp_path / "chosen"
    storage.update_media_root(chosen_root)
    pipeline = TranscriptionPipeline(
        repository, FakeBrowser(), FakeDownloader(), FakeAudioExtractor(),
        FakeTranscriber(), storage, cover_extractor=FakeCoverExtractor(),
    )

    await pipeline.execute("details")

    job = repository.get("details")
    assert job.status is JobStatus.COMPLETED
    media = job.result.media
    assert Path(media.cover_path).read_bytes() == b"test cover jpeg"
    assert Path(media.title_path).read_text(encoding="utf-8") == "测试视频"
    assert Path(media.cover_path).parent == chosen_root / "videos" / "测试视频"
    assert Path(media.title_path).parent == chosen_root / "videos" / "测试视频"
    assert Path(media.absolute_path).exists() is save_video
    assert not (chosen_root / "work" / "details").exists()


async def test_cover_and_title_remain_saved_if_transcription_fails(tmp_path: Path) -> None:
    class FailedTranscriber:
        async def transcribe(self, *args) -> Transcript:
            raise TranscriptionFailedError()

    repository = InMemoryJobRepository()
    repository.add(Job("failed-asr", "https://v.douyin.com/test/", "zh", save_video=False))
    storage = LocalStorage(tmp_path / "work", tmp_path / "videos")
    pipeline = TranscriptionPipeline(
        repository, FakeBrowser(), FakeDownloader(), FakeAudioExtractor(),
        FailedTranscriber(), storage, cover_extractor=FakeCoverExtractor(),
    )

    await pipeline.execute("failed-asr")

    assert repository.get("failed-asr").status is JobStatus.FAILED
    assert len(list(storage.videos_root.rglob("封面.jpg"))) == 1
    assert next(storage.videos_root.rglob("标题.txt")).read_text() == "测试视频"
    assert set(repository.get("failed-asr").metadata["source_files"]) == {
        str(path.resolve()) for path in (storage.videos_root / "测试视频").iterdir()
    }
    assert not list(storage.videos_root.rglob("*.mp4"))
    assert not (storage.work_root / "failed-asr").exists()


class FakeTranscriber:
    async def transcribe(self, audio_path, language, work_dir, progress) -> Transcript:
        assert audio_path.is_file()
        progress(80, "识别中")
        return Transcript(
            text="你好",
            detected_language="zh",
            segments=(TranscriptSegment(0, 1000, "你好"),),
        )


@pytest.mark.parametrize("save_video", [True, False])
async def test_download_without_txt_skips_audio_and_transcriber(tmp_path, save_video):
    class UnusedAudio:
        async def extract(self, *args):
            raise AssertionError("TXT disabled must not extract audio")

    class UnusedTranscriber:
        async def transcribe(self, *args):
            raise AssertionError("TXT disabled must not run speech model")

    repository = InMemoryJobRepository()
    repository.add(Job("no-txt", "https://www.douyin.com/video/123", "zh",
                       save_video=save_video, extract_txt=False))
    storage = LocalStorage(tmp_path / "work", tmp_path / "videos")
    pipeline = TranscriptionPipeline(repository, FakeBrowser(), FakeDownloader(), UnusedAudio(),
                                     UnusedTranscriber(), storage, cover_extractor=FakeCoverExtractor())
    await pipeline.execute("no-txt")
    job = repository.get("no-txt")
    assert job.status is JobStatus.COMPLETED
    assert job.result.transcript is None
    assert job.message == "视频处理完成"
    assert Path(job.result.media.absolute_path).is_file() is save_video
    assert Path(job.result.media.cover_path).is_file()
    assert Path(job.result.media.title_path).is_file()


async def test_internal_source_does_not_reuse_or_overwrite_legacy_video(tmp_path: Path) -> None:
    class InternalBrowser(FakeBrowser):
        async def acquire(self, url: str, cookie_file: Path, *, on_state=None) -> BrowserEvidence:
            cookie_file.write_text("# Netscape HTTP Cookie File\n")
            return BrowserEvidence(url, "fake-agent", cookie_file, MediaMetadata(
                "123", "新版作品", duration=5.0, video_source_policy="douyin-internal-v1",
            ))

    repository = InMemoryJobRepository()
    repository.add(Job("internal", "https://www.douyin.com/video/123", "zh", save_video=True))
    storage = LocalStorage(tmp_path / "work", tmp_path / "videos")
    original = tmp_path / "original.mp4"
    original.write_bytes(b"old shared video")
    old_path = storage.publish_video(original, "123")
    old_cover = tmp_path / "old.jpg"
    old_cover.write_bytes(b"old cover")
    cover, title = storage.publish_video_details(old_cover, "旧标题", "123")
    downloader = BrowserMetadataDownloader()
    pipeline = TranscriptionPipeline(
        repository, InternalBrowser(), downloader, FakeAudioExtractor(),
        FakeTranscriber(), storage, cover_extractor=FakeCoverExtractor(),
    )

    await pipeline.execute("internal")

    job = repository.get("internal")
    assert job.status is JobStatus.COMPLETED
    assert downloader.downloads == 1
    assert old_path.read_bytes() == b"old shared video"
    assert cover.read_bytes() == b"old cover"
    assert title.read_text() == "旧标题"
    assert Path(job.result.media.absolute_path) != old_path
    assert storage.find_video("123_douyin-internal-v1") == Path(job.result.media.absolute_path)


async def test_pipeline_limits_ffmpeg_and_whisper_and_deduplicates_downloads(
    tmp_path: Path,
) -> None:
    class BlockingAudioExtractor(FakeAudioExtractor):
        def __init__(self) -> None:
            self.active = 0
            self.maximum_active = 0
            self.two_started = asyncio.Event()
            self.release = asyncio.Event()

        async def extract(self, video_path: Path, audio_path: Path) -> None:
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
            if self.active == 2:
                self.two_started.set()
            try:
                await self.release.wait()
                await super().extract(video_path, audio_path)
            finally:
                self.active -= 1

    class BlockingTranscriber(FakeTranscriber):
        def __init__(self) -> None:
            self.active = 0
            self.maximum_active = 0
            self.two_started = asyncio.Event()
            self.release = asyncio.Event()

        async def transcribe(self, audio_path, language, work_dir, progress) -> Transcript:
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
            if self.active == 2:
                self.two_started.set()
            try:
                await self.release.wait()
                return await super().transcribe(audio_path, language, work_dir, progress)
            finally:
                self.active -= 1

    repository = InMemoryJobRepository()
    storage = LocalStorage(tmp_path / "work", tmp_path / "videos")
    downloader = FakeDownloader()
    audio_extractor = BlockingAudioExtractor()
    transcriber = BlockingTranscriber()
    pipeline = TranscriptionPipeline(
        repository,
        FakeBrowser(),
        downloader,
        audio_extractor,
        transcriber,
        storage,
        ffmpeg_concurrency=2,
        whisper_concurrency=2,
    )
    for job_id in ("one", "two", "three"):
        repository.add(Job(job_id, "https://v.douyin.com/test/", "zh"))

    tasks = [asyncio.create_task(pipeline.execute(job_id)) for job_id in ("one", "two", "three")]
    await asyncio.wait_for(audio_extractor.two_started.wait(), timeout=1)
    assert audio_extractor.active == 2
    audio_extractor.release.set()

    await asyncio.wait_for(transcriber.two_started.wait(), timeout=1)
    assert transcriber.active == 2
    transcriber.release.set()
    await asyncio.gather(*tasks)

    assert audio_extractor.maximum_active == 2
    assert transcriber.maximum_active == 2
    assert downloader.downloads == 1
    assert pipeline._media_locks == {}
    assert all(
        repository.get(job_id).status is JobStatus.COMPLETED for job_id in ("one", "two", "three")
    )


async def test_pipeline_limits_downloads_to_five(tmp_path: Path) -> None:
    class UniqueMetadataBrowser(FakeBrowser):
        async def acquire(self, url: str, cookie_file: Path, *, on_state=None) -> BrowserEvidence:
            job_id = cookie_file.parent.name
            cookie_file.write_text("# Netscape HTTP Cookie File\n")
            return BrowserEvidence(
                f"https://www.douyin.com/video/{job_id}",
                "fake-agent",
                cookie_file,
                MediaMetadata(job_id, f"视频 {job_id}", duration=5.0),
            )

    class BlockingDownloader(FakeDownloader):
        def __init__(self) -> None:
            self.active = 0
            self.maximum_active = 0
            self.five_started = asyncio.Event()
            self.release = asyncio.Event()

        async def download(
            self, url, metadata, cookie_file, user_agent, work_dir, progress
        ) -> Path:
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
            if self.active == 5:
                self.five_started.set()
            try:
                await self.release.wait()
                output = work_dir / f"{metadata.id}.mp4"
                output.write_bytes(b"fake mp4")
                return output
            finally:
                self.active -= 1

    repository = InMemoryJobRepository()
    downloader = BlockingDownloader()
    pipeline = TranscriptionPipeline(
        repository,
        UniqueMetadataBrowser(),
        downloader,
        FakeAudioExtractor(),
        FakeTranscriber(),
        LocalStorage(tmp_path / "work", tmp_path / "videos"),
        download_concurrency=5,
        ffmpeg_concurrency=6,
        whisper_concurrency=6,
    )
    job_ids = tuple(f"job-{index}" for index in range(6))
    for job_id in job_ids:
        repository.add(Job(job_id, "https://v.douyin.com/test/", "zh"))

    tasks = [asyncio.create_task(pipeline.execute(job_id)) for job_id in job_ids]
    try:
        await asyncio.wait_for(downloader.five_started.wait(), timeout=1)
        assert downloader.active == 5
    finally:
        downloader.release.set()
        await asyncio.gather(*tasks)

    assert downloader.maximum_active == 5
    assert all(repository.get(job_id).status is JobStatus.COMPLETED for job_id in job_ids)


async def test_pipeline_completes_and_reuses_video(tmp_path: Path) -> None:
    repository = InMemoryJobRepository()
    storage = LocalStorage(tmp_path / "work", tmp_path / "videos")
    downloader = FakeDownloader()
    pipeline = TranscriptionPipeline(
        repository,
        FakeBrowser(),
        downloader,
        FakeAudioExtractor(),
        FakeTranscriber(),
        storage,
    )

    for job_id in ("one", "two"):
        repository.add(Job(job_id, "复制链接 https://v.douyin.com/test/", "zh"))
        await pipeline.execute(job_id)
        job = repository.get(job_id)
        assert job.status is JobStatus.COMPLETED
        assert job.result.transcript.text == "你好"
        assert not (tmp_path / "work" / job_id).exists()

    assert downloader.downloads == 1
    saved_videos = list((tmp_path / "videos").rglob("*.mp4"))
    assert len(saved_videos) == 1
    assert saved_videos[0].name == "视频.mp4"
    assert saved_videos[0].read_bytes() == b"fake mp4"


async def test_pipeline_logs_critical_job_stages(tmp_path: Path, caplog) -> None:
    repository = InMemoryJobRepository()
    repository.add(Job("logged-job", "https://v.douyin.com/test/", "zh"))
    pipeline = TranscriptionPipeline(
        repository,
        FakeBrowser(),
        FakeDownloader(),
        FakeAudioExtractor(),
        FakeTranscriber(),
        LocalStorage(tmp_path / "work", tmp_path / "videos"),
    )
    caplog.set_level(logging.INFO, logger="voxpull.application.pipeline")

    await pipeline.execute("logged-job")

    messages = [record.getMessage() for record in caplog.records]
    for event in (
        "event=pipeline_started",
        "event=cookie_acquisition_started",
        "event=media_identified",
        "event=video_download_started",
        "event=audio_extraction_started",
        "event=transcription_started",
        "event=pipeline_completed",
    ):
        assert any("job_id=logged-job" in message and event in message for message in messages)


async def test_pipeline_deletes_temporary_video_when_saving_is_disabled(
    tmp_path: Path,
) -> None:
    repository = InMemoryJobRepository()
    repository.add(Job("temporary", "复制链接 https://v.douyin.com/test/", "zh", save_video=False))
    storage = LocalStorage(tmp_path / "work", tmp_path / "videos")
    selected_root = tmp_path / "selected-media"
    storage.update_media_root(selected_root)
    pipeline = TranscriptionPipeline(
        repository,
        FakeBrowser(),
        FakeDownloader(),
        FakeAudioExtractor(),
        FakeTranscriber(),
        storage,
    )

    await pipeline.execute("temporary")

    job = repository.get("temporary")
    assert job is not None
    assert job.status is JobStatus.COMPLETED
    assert job.result is not None
    assert job.result.media.saved is False
    temporary_path = Path(job.result.media.absolute_path)
    assert temporary_path.parent == (selected_root / "videos" / "测试视频").resolve()
    assert temporary_path.suffix == ".mp4"
    assert temporary_path.name == "视频.mp4"
    assert temporary_path.stem.isalnum()
    assert not temporary_path.exists()
    assert not list((selected_root / "videos").rglob("*.mp4"))
    assert (temporary_path.parent / "文案.txt").read_text() == "你好"


async def test_temporary_job_does_not_delete_an_already_saved_video(
    tmp_path: Path,
) -> None:
    repository = InMemoryJobRepository()
    repository.add(Job("temporary", "复制链接 https://v.douyin.com/test/", "zh", save_video=False))
    storage = LocalStorage(tmp_path / "work", tmp_path / "videos")
    saved_video = tmp_path / "videos" / "123.mp4"
    saved_video.write_bytes(b"previously saved mp4")
    downloader = FakeDownloader()
    pipeline = TranscriptionPipeline(
        repository,
        FakeBrowser(),
        downloader,
        FakeAudioExtractor(),
        FakeTranscriber(),
        storage,
    )

    await pipeline.execute("temporary")

    assert downloader.downloads == 1
    assert saved_video.read_bytes() == b"previously saved mp4"


async def test_pipeline_uses_browser_metadata_without_probing(tmp_path: Path) -> None:
    class MetadataBrowser(FakeBrowser):
        async def acquire(self, url: str, cookie_file: Path, *, on_state=None) -> BrowserEvidence:
            cookie_file.write_text("# Netscape HTTP Cookie File\n")
            return BrowserEvidence(
                "https://www.douyin.com/video/123",
                "fake-agent",
                cookie_file,
                MediaMetadata(
                    "123",
                    "页面返回的视频",
                    duration=5.0,
                    source_urls=("https://cdn.example/123.mp4",),
                ),
            )

    repository = InMemoryJobRepository()
    repository.add(Job("browser-detail", "https://v.douyin.com/test/", "zh"))
    storage = LocalStorage(tmp_path / "work", tmp_path / "videos")
    pipeline = TranscriptionPipeline(
        repository,
        MetadataBrowser(),
        BrowserMetadataDownloader(),
        FakeAudioExtractor(),
        FakeTranscriber(),
        storage,
    )

    await pipeline.execute("browser-detail")

    job = repository.get("browser-detail")
    assert job is not None
    assert job.status is JobStatus.COMPLETED
    assert job.result is not None
    assert job.result.media.title == "页面返回的视频"


async def test_pipeline_downloads_non_douyin_url_without_browser(tmp_path: Path) -> None:
    direct_url = "https://vod.dkhs.com/path/example.mp4"

    class BrowserMustNotRun(FakeBrowser):
        async def acquire(self, url: str, cookie_file: Path, *, on_state=None) -> BrowserEvidence:
            raise AssertionError("non-Douyin URLs must bypass the browser")

    class DirectDownloader(FakeDownloader):
        async def probe(self, url: str, cookie_file: Path, user_agent: str) -> MediaMetadata:
            assert url == direct_url
            assert cookie_file.read_text(encoding="utf-8") == "# Netscape HTTP Cookie File\n"
            assert user_agent.startswith("Mozilla/5.0")
            return MediaMetadata("123", "直链视频", duration=5.0)

        async def download(
            self, url, metadata, cookie_file, user_agent, work_dir, progress
        ) -> Path:
            assert url == direct_url
            return await super().download(
                url, metadata, cookie_file, user_agent, work_dir, progress
            )

    repository = InMemoryJobRepository()
    repository.add(Job("direct", direct_url, "zh"))
    storage = LocalStorage(tmp_path / "work", tmp_path / "videos")
    pipeline = TranscriptionPipeline(
        repository,
        BrowserMustNotRun(),
        DirectDownloader(),
        FakeAudioExtractor(),
        FakeTranscriber(),
        storage,
    )

    await pipeline.execute("direct")

    job = repository.get("direct")
    assert job is not None
    assert job.status is JobStatus.COMPLETED
    assert job.result is not None
    assert job.result.media.title == "直链视频"


async def test_pipeline_saves_image_post_in_its_own_folder_without_transcription(
    tmp_path: Path,
) -> None:
    class ImageDownloader(FakeDownloader):
        async def probe(self, url: str, cookie_file: Path, user_agent: str) -> MediaMetadata:
            return MediaMetadata(
                id="gallery-123",
                title="七张 Live 图",
                description="图文正文\n保留换行与话题 #旅行#",
                kind=MediaKind.IMAGES,
                images=(
                    ImageAssetMetadata(
                        index=1,
                        source_urls=("https://cdn.example/one.webp",),
                        motion_urls=("https://cdn.example/one.mp4",),
                    ),
                    ImageAssetMetadata(
                        index=2,
                        source_urls=("https://cdn.example/two.jpg",),
                    ),
                ),
            )

        async def download_images(
            self, url, metadata, cookie_file, user_agent, work_dir, progress
        ) -> Path:
            folder = work_dir / "images"
            folder.mkdir()
            (folder / "001.webp").write_bytes(b"first image")
            (folder / "001.live.mp4").write_bytes(b"motion")
            (folder / "002.jpg").write_bytes(b"second image")
            (folder / "manifest.json").write_text("{}", encoding="utf-8")
            progress(100, "图片已保存")
            return folder

    class AudioMustNotRun(FakeAudioExtractor):
        async def extract(self, video_path: Path, audio_path: Path) -> None:
            raise AssertionError("image posts must not enter audio extraction")

    class TranscriberMustNotRun(FakeTranscriber):
        async def transcribe(self, audio_path, language, work_dir, progress) -> Transcript:
            raise AssertionError("image posts must not enter transcription")

    repository = InMemoryJobRepository()
    repository.add(
        Job(
            "gallery",
            "https://www.xiaohongshu.com/discovery/item/gallery-123",
            "zh",
            save_video=False,
        )
    )
    storage = LocalStorage(
        tmp_path / "work",
        tmp_path / "videos",
        tmp_path / "images",
    )
    pipeline = TranscriptionPipeline(
        repository,
        FakeBrowser(),
        ImageDownloader(),
        AudioMustNotRun(),
        TranscriberMustNotRun(),
        storage,
    )

    await pipeline.execute("gallery")

    job = repository.get("gallery")
    assert job is not None
    assert job.status is JobStatus.COMPLETED
    assert job.result is not None
    assert job.result.transcript is None
    assert job.result.media.kind is MediaKind.IMAGES
    assert job.result.media.saved is True
    assert job.result.media.description == "图文正文\n保留换行与话题 #旅行#"
    assert Path(job.result.media.description_path).read_text() == job.result.media.description
    from voxpull.api.schemas import job_to_response
    assert job_to_response(job).result.media.description == job.result.media.description
    assert str(Path(job.result.media.description_path)) in job.metadata["source_files"]
    assert job.result.media.asset_count == 2
    assert job.result.media.live_photo_count == 1
    folder = Path(job.result.media.absolute_path)
    assert folder.parent == tmp_path / "images"
    assert folder.name == "七张 Live 图"
    assert job.result.media.filename == folder.name
    assert sorted(path.name for path in folder.iterdir()) == [
        "manifest.json",
        "图片1.webp",
        "图片2.jpg",
        "封面.webp",
        "文案.txt",
        "标题.txt",
        "视频1.mp4",
    ]


async def test_pipeline_does_not_publish_a_failed_image_gallery(tmp_path: Path) -> None:
    class FailingImageDownloader(FakeDownloader):
        async def probe(self, url: str, cookie_file: Path, user_agent: str) -> MediaMetadata:
            return MediaMetadata(
                id="gallery-failed",
                title="失败图集",
                kind=MediaKind.IMAGES,
                images=(
                    ImageAssetMetadata(
                        index=1,
                        source_urls=("https://cdn.example/one.webp",),
                    ),
                ),
            )

        async def download_images(
            self, url, metadata, cookie_file, user_agent, work_dir, progress
        ) -> Path:
            folder = work_dir / "images"
            folder.mkdir()
            (folder / ".001.part").write_bytes(b"partial")
            raise DownloadFailedError("图片下载失败")

    repository = InMemoryJobRepository()
    repository.add(
        Job(
            "gallery-failed",
            "https://www.xiaohongshu.com/discovery/item/gallery-failed",
            "zh",
            save_video=False,
        )
    )
    storage = LocalStorage(
        tmp_path / "work",
        tmp_path / "videos",
        tmp_path / "images",
    )
    pipeline = TranscriptionPipeline(
        repository,
        FakeBrowser(),
        FailingImageDownloader(),
        FakeAudioExtractor(),
        FakeTranscriber(),
        storage,
    )

    await pipeline.execute("gallery-failed")

    job = repository.get("gallery-failed")
    assert job is not None
    assert job.status is JobStatus.FAILED
    assert not (tmp_path / "work" / "gallery-failed").exists()
    assert not list((tmp_path / "images").iterdir())
