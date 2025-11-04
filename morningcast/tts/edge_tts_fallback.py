"""Fallback edge-tts engine."""
from __future__ import annotations

import asyncio
import html
import re
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

    def synthesize(self, *, plain_text: str, ssml: str, output_path: Path) -> None:
        if edge_tts is None:
            raise RuntimeError("edge-tts is not installed") from _IMPORT_ERROR  # type: ignore[name-defined]

        text = plain_text.strip()
        if not text and ssml.strip():
            text = self._ssml_to_plain_text(ssml)

        if not text:
            raise ValueError("No readable text available for Edge TTS synthesis")

        asyncio.run(self._synthesize(text, output_path))

    async def _synthesize(self, text: str, output_path: Path) -> None:
        if edge_tts is None:
            raise RuntimeError("edge-tts is not installed") from _IMPORT_ERROR  # type: ignore[name-defined]
        communicate = edge_tts.Communicate(text=text, voice=self.voice)
        await communicate.save(str(output_path))

    @staticmethod
    def _ssml_to_plain_text(ssml: str) -> str:
        text = re.sub(r"<\/?speak[^>]*>", " ", ssml, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.replace("\xa0", " ")
        return html.unescape(text.strip())
