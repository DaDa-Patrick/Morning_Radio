"""Audio mixing utilities for MorningCast."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import ffmpeg


@dataclass(slots=True)
class SongSegmentPlan:
    source: Path
    start: float
    duration: float
    fade_in: float = 1.5
    fade_out: float = 2.5


def extract_segment(plan: SongSegmentPlan, output_path: Path) -> Path:
    stream = (
        ffmpeg
        .input(str(plan.source), ss=max(plan.start - plan.fade_in, 0), t=plan.duration + plan.fade_in + plan.fade_out)
        .filter("afade", t="in", st=0, d=plan.fade_in)
        .filter("afade", t="out", st=plan.duration + plan.fade_in, d=plan.fade_out)
    )
    ffmpeg.output(stream, str(output_path), ac=2).overwrite_output().run(quiet=True)
    return output_path


def crossfade_tracks(tracks: Iterable[Path], output_path: Path, crossfade: float = 4.0) -> Path:
    paths = list(tracks)
    if not paths:
        raise ValueError("At least one track is required")
    if len(paths) == 1:
        ffmpeg.output(ffmpeg.input(str(paths[0])), str(output_path)).overwrite_output().run(quiet=True)
        return output_path

    inputs = [ffmpeg.input(str(path)) for path in paths]
    current = inputs[0]
    for nxt in inputs[1:]:
        current = ffmpeg.filter([current, nxt], "acrossfade", d=crossfade, c1="tri", c2="tri")
    ffmpeg.output(current, str(output_path)).overwrite_output().run(quiet=True)
    return output_path


def duck_voice_over(music_path: Path, voice_path: Path, output_path: Path) -> Path:
    """Apply sidechain compression so the voice track leads."""
    music = ffmpeg.input(str(music_path))
    voice = ffmpeg.input(str(voice_path))
    compressed = ffmpeg.filter(
        [music.audio, voice.audio],
        "sidechaincompress",
        threshold="-18dB",
        ratio=6,
        attack=12,
        release=200,
    )
    mix = ffmpeg.filter([compressed, voice.audio], "amix", inputs=2, dropout_transition=0)
    ffmpeg.output(mix, str(output_path), ac=2).overwrite_output().run(quiet=True)
    return output_path


def export_with_metadata(source: Path, target: Path, metadata: Optional[dict] = None, cover: Optional[Path] = None) -> Path:
    stream = ffmpeg.input(str(source))
    codec = "mp3" if target.suffix.lower() == ".mp3" else "aac"
    metadata_args = {f"metadata:g:{key}": value for key, value in (metadata or {}).items()}
    if cover and cover.exists():
        cover_stream = ffmpeg.input(str(cover))
        output = ffmpeg.output(stream, cover_stream, str(target), acodec=codec, **metadata_args)
    else:
        output = ffmpeg.output(stream, str(target), acodec=codec, **metadata_args)
    ffmpeg.run(output, overwrite_output=True, quiet=True)
    return target
