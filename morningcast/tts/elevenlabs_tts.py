"""ElevenLabs TTS implementation."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import requests

from .base import TextToSpeechEngine


class ElevenLabsTTSEngine(TextToSpeechEngine):  # pragma: no cover - network service
    def __init__(self, api_key: str | None = None, voice_id: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise RuntimeError("ElevenLabs API key missing")
        self.voice_id = voice_id or os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    def synthesize(self, *, plain_text: str, ssml: str, output_path: Path) -> None:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
        headers = {"xi-api-key": self.api_key}
        payload = {
            "text": plain_text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.8},
        }
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        output_path.write_bytes(response.content)
