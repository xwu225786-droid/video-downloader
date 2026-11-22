from voxpull.application.exporters import format_timestamp, to_srt, to_timeline_text
from voxpull.domain.models import Transcript, TranscriptSegment


def sample_transcript() -> Transcript:
    return Transcript(
        text="第一句\n第二句",
        detected_language="zh",
        segments=(
            TranscriptSegment(0, 1234, "第一句"),
            TranscriptSegment(61_001, 62_345, "第二句"),
        ),
    )


def test_timestamp_formats() -> None:
    assert format_timestamp(3_661_234) == "01:01:01.234"
    assert format_timestamp(3_661_234, srt=True) == "01:01:01,234"


def test_timeline_and_srt_are_deterministic() -> None:
    transcript = sample_transcript()
    assert to_timeline_text(transcript).splitlines()[0] == "[00:00:00.000 --> 00:00:01.234] 第一句"
    assert to_srt(transcript) == (
        "1\n00:00:00,000 --> 00:00:01,234\n第一句\n\n2\n00:01:01,001 --> 00:01:02,345\n第二句\n"
    )
