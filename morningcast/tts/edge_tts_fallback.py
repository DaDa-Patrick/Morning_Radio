"""Fallback edge-tts engine."""
from __future__ import annotations

import asyncio
import html
import re
import unicodedata
from pathlib import Path

_IMPORT_ERROR = None
try:  # pragma: no cover - optional dependency
    import edge_tts
except ImportError as exc:  # pragma: no cover - optional dependency
    edge_tts = None  # type: ignore
    _IMPORT_ERROR = exc

from ..utils.logging import get_logger
from .base import TextToSpeechEngine

logger = get_logger(__name__)


class EdgeTTSEngine(TextToSpeechEngine):  # pragma: no cover - async network call
    def __init__(self, voice: str = "zh-TW-HsiaoChenNeural"):
        self.voice = voice

    def synthesize(self, *, plain_text: str, ssml: str, output_path: Path) -> None:
        if edge_tts is None:
            raise RuntimeError("edge-tts is not installed") from _IMPORT_ERROR  # type: ignore[name-defined]

        text = self._prepare_text(plain_text=plain_text, ssml=ssml)

        logger.debug("Edge TTS rendering %d characters", len(text))
        asyncio.run(self._synthesize(text, output_path))

    def _prepare_text(self, *, plain_text: str, ssml: str) -> str:
        """Return a clean plain-text payload that Edge TTS can read."""

        text = plain_text.strip()
        if not text and ssml.strip():
            text = self._ssml_to_plain_text(ssml)

        text = self._normalise_text(text)
        if not text:
            raise ValueError("No readable text available for Edge TTS synthesis")
        return text

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

    @staticmethod
    def _normalise_text(text: str) -> str:
        """Strip unsupported characters and compress whitespace."""

        if not text:
            return ""

        text = unicodedata.normalize("NFKC", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Remove any lingering markup braces or brackets that trip SSML parsing.
        text = re.sub(r"[<>\[\]{}]", " ", text)

        cleaned_chars = []
        for char in text:
            category = unicodedata.category(char)
            if category.startswith("C"):
                # Skip control characters entirely.
                continue
            if category in {"Sk", "So"}:
                # Replace emojis or other symbols with a readable pause.
                cleaned_chars.append(" ")
                continue
            cleaned_chars.append(char)

        collapsed = "".join(cleaned_chars)
        collapsed = re.sub(r"\s+", " ", collapsed)
        return collapsed.strip()
