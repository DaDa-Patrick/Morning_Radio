"""Base TTS interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TextToSpeechEngine(ABC):
    @abstractmethod
    def synthesize_ssml(self, ssml: str, output_path: Path) -> None:  # pragma: no cover - I/O heavy
        """Render SSML to an audio file."""
        raise NotImplementedError
