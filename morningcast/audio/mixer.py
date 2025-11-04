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


def duck_voice_over(
    music_path: Path,
    voice_path: Path,
    output_path: Path,
    *,
    music_gain_db: float = -18.0,
    voice_gain_db: float = 0.0,
    target_lufs: float = -16.0,
) -> Path:
    """Blend the host voice with a subdued music bed using sidechain ducking."""

    music = ffmpeg.input(str(music_path))
    voice = ffmpeg.input(str(voice_path))

    music_audio = music.audio.filter_("volume", volume=f"{music_gain_db}dB")
    voice_audio = voice.audio.filter_("volume", volume=f"{voice_gain_db}dB")

    ducked_music = ffmpeg.filter(
        [music_audio, voice_audio],
        "sidechaincompress",
        threshold="-28dB",
        ratio=12,
        attack=8,
        release=350,
        makeup=6,
    )

    mixed = ffmpeg.filter([ducked_music, voice_audio], "amix", inputs=2, dropout_transition=0)
    mixed = mixed.filter_(
        "alimiter",
        limit="-1dB",
        level="disabled",
    )
    mixed = mixed.filter_(
        "loudnorm",
        I=str(target_lufs),
        TP="-1.5",
        LRA="11",
    )

    ffmpeg.output(mixed, str(output_path), ac=2, ar=44100).overwrite_output().run(quiet=True)
    return output_path


def append_full_song(
    prefix_path: Path,
    song_path: Path,
    output_path: Path,
    *,
    gap_seconds: float = 1.5,
    song_fade_in: float = 2.5,
) -> Path:
    """Append the requested full song after the spoken programme."""

    prefix = ffmpeg.input(str(prefix_path))
    song = ffmpeg.input(str(song_path))

    song_audio = song.audio
    if song_fade_in > 0:
        song_audio = song_audio.filter("afade", t="in", d=song_fade_in)

    streams = [prefix.audio]
    if gap_seconds > 0:
        silence = ffmpeg.input(
            "anullsrc=r=44100:cl=stereo",
            f="lavfi",
            t=gap_seconds,
        )
        streams.append(silence.audio)
    streams.append(song_audio)

    concatenated = ffmpeg.concat(*streams, v=0, a=1)
    ffmpeg.output(concatenated, str(output_path), ac=2, ar=44100).overwrite_output().run(quiet=True)
    return output_path


def export_with_metadata(source: Path, target: Path, metadata: Optional[dict] = None, cover: Optional[Path] = None) -> Path:
    stream = ffmpeg.input(str(source))
    suffix = target.suffix.lower()
    if suffix == ".mp3":
        codec = "libmp3lame"
    elif suffix in {".aac", ".m4a"}:
        codec = "aac"
    elif suffix == ".wav":
        codec = "pcm_s16le"
    else:
        codec = "copy"

    output_streams = [stream]
    output_kwargs = {"acodec": codec}

    if cover and cover.exists():
        cover_stream = ffmpeg.input(str(cover))
        output_streams.append(cover_stream)
        output = ffmpeg.output(
            *output_streams,
            str(target),
            **output_kwargs,
            vcodec="mjpeg",
            map=["0:a", "1:v"],
            id3v2_version="3",
        )
        output = output.global_args(
            "-metadata:s:v:0",
            "title=Album cover",
            "-metadata:s:v:0",
            "comment=Cover (Front)",
            "-disposition:v:0",
            "attached_pic",
        )
    else:
        output = ffmpeg.output(*output_streams, str(target), **output_kwargs)

    if metadata:
        for key, value in metadata.items():
            if value is None:
                continue
            output = output.global_args("-metadata", f"{key}={value}")

    ffmpeg.run(output, overwrite_output=True, quiet=True)
    return target
