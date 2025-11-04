"""Fallback edge-tts engine."""
from __future__ import annotations

import asyncio
from pathlib import Path

_IMPORT_ERROR = None
try:  # pragma: no cover - optional dependency
    import edge_tts
except ImportError as exc:  # pragma: no cover - optional dependency
    edge_tts = None  # type: ignore
    _IMPORT_ERROR = exc

from .base import TextToSpeechEngine


class EdgeTTSEngine(TextToSpeechEngine):  # pragma: no cover - async network call
    def __init__(self, voice: str = "zh-TW-HsiaoChenNeural"):
        self.voice = voice

    def synthesize_ssml(self, ssml: str, output_path: Path) -> None:
        if edge_tts is None:
            raise RuntimeError("edge-tts is not installed") from _IMPORT_ERROR  # type: ignore[name-defined]
        asyncio.run(self._synthesize(ssml, output_path))

    async def _synthesize(self, ssml: str, output_path: Path) -> None:
        if edge_tts is None:
            raise RuntimeError("edge-tts is not installed") from _IMPORT_ERROR  # type: ignore[name-defined]
        communicate = edge_tts.Communicate(ssml=ssml, voice=self.voice)
        await communicate.save(str(output_path))
