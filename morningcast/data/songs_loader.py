"""Utilities for loading local song metadata."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass(slots=True)
class SongMetadata:
    title: str
    artist: Optional[str]
    path: Path
    bpm: Optional[float]
    energy: Optional[float]


FIELD_ALIASES = {
    "title": {"title", "name"},
    "artist": {"artist", "singer"},
    "path": {"path", "filepath", "file"},
    "bpm": {"bpm", "tempo"},
    "energy": {"energy", "intensity"},
}


def _normalise_header(header: Iterable[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for column in header:
        lowered = column.strip().lower()
        for canonical, aliases in FIELD_ALIASES.items():
            if lowered in aliases:
                mapping[column] = canonical
                break
    return mapping


def load_songs(csv_path: str | Path) -> List[SongMetadata]:
    """Load songs metadata from a CSV file."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        mapping = _normalise_header(reader.fieldnames or [])
        songs: List[SongMetadata] = []
        for row in reader:
            normalised = {mapping.get(key, key): value for key, value in row.items()}
            songs.append(
                SongMetadata(
                    title=normalised.get("title") or "Unknown",
                    artist=normalised.get("artist"),
                    path=Path(normalised.get("path") or ""),
                    bpm=float(normalised["bpm"]) if normalised.get("bpm") else None,
                    energy=float(normalised["energy"]) if normalised.get("energy") else None,
                )
            )
    return songs
