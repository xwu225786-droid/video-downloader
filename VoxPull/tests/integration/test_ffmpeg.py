import shutil
from pathlib import Path

import pytest

from voxpull.infrastructure.audio import FfmpegAudioExtractor
from voxpull.infrastructure.cover import FfmpegCoverExtractor
from voxpull.infrastructure.processes import ProcessRunner


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
async def test_real_ffmpeg_adapter_creates_pcm_wav(tmp_path: Path) -> None:
    runner = ProcessRunner()
    source = tmp_path / "source.mp4"
    output = tmp_path / "audio.wav"
    try:
        generated = await runner.run(
            (
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=0.1",
                "-c:a",
                "aac",
                str(source),
            ),
            timeout=10,
        )
        assert generated.returncode == 0

        await FfmpegAudioExtractor(runner, "ffmpeg", 10).extract(source, output)
        assert output.read_bytes().startswith(b"RIFF")
        assert output.stat().st_size > 3_000
    finally:
        await runner.close()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
async def test_cover_is_the_first_frame_rather_than_a_later_frame(tmp_path: Path) -> None:
    from PIL import Image

    runner = ProcessRunner()
    source = tmp_path / "two-colors.mp4"
    cover = tmp_path / "cover.jpg"
    try:
        generated = await runner.run(
            (
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=red:s=64x48:r=10:d=0.2",
                "-f", "lavfi", "-i", "color=c=blue:s=64x48:r=10:d=0.2",
                "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[out]",
                "-map", "[out]", "-c:v", "libx264", str(source),
            ),
            timeout=10,
        )
        assert generated.returncode == 0
        await FfmpegCoverExtractor(runner, "ffmpeg", 10).extract(source, cover)
        with Image.open(cover) as image:
            assert image.size == (64, 48)
            red, green, blue = image.convert("RGB").getpixel((32, 24))
            assert red > 200 and green < 30 and blue < 30
    finally:
        await runner.close()
