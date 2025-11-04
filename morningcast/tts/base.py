"""Base TTS interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TextToSpeechEngine(ABC):
    @abstractmethod
    def synthesize(self, *, plain_text: str, ssml: str, output_path: Path) -> None:  # pragma: no cover - I/O heavy
        """Render speech from either plain text or SSML."""
        raise NotImplementedError
