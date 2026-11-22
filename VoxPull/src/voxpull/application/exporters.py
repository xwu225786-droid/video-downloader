from __future__ import annotations

from voxpull.domain.models import Transcript


def format_timestamp(milliseconds: int, *, srt: bool = False) -> str:
    milliseconds = max(0, milliseconds)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    separator = "," if srt else "."
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{millis:03d}"


def to_timeline_text(transcript: Transcript) -> str:
    return "\n".join(
        f"[{format_timestamp(segment.start_ms)} --> {format_timestamp(segment.end_ms)}] "
        f"{segment.text}"
        for segment in transcript.segments
    )


def to_srt(transcript: Transcript) -> str:
    blocks = []
    for index, segment in enumerate(transcript.segments, start=1):
        blocks.append(
            f"{index}\n"
            f"{format_timestamp(segment.start_ms, srt=True)} --> "
            f"{format_timestamp(segment.end_ms, srt=True)}\n"
            f"{segment.text}"
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")
