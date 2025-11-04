"""Azure Speech Service implementation."""
from __future__ import annotations

import os
from pathlib import Path

_IMPORT_ERROR = None
try:  # pragma: no cover - optional dependency
    import azure.cognitiveservices.speech as speechsdk
except ImportError as exc:  # pragma: no cover - optional dependency
    speechsdk = None  # type: ignore
    _IMPORT_ERROR = exc

from .base import TextToSpeechEngine


class AzureTTSEngine(TextToSpeechEngine):  # pragma: no cover - network service
    def __init__(self, key: str | None = None, region: str | None = None):
        if speechsdk is None:
            raise RuntimeError("Azure Speech SDK is not installed") from _IMPORT_ERROR  # type: ignore[name-defined]
        self.key = key or os.environ.get("AZURE_SPEECH_KEY")
        self.region = region or os.environ.get("AZURE_SPEECH_REGION")
        if not self.key or not self.region:
            raise RuntimeError("Azure TTS credentials are missing")

    def synthesize(self, *, plain_text: str, ssml: str, output_path: Path) -> None:
        speech_config = speechsdk.SpeechConfig(subscription=self.key, region=self.region)
        audio_cfg = speechsdk.audio.AudioOutputConfig(filename=str(output_path))
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_cfg)
        result = synthesizer.speak_ssml_async(ssml).get()
        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            raise RuntimeError(f"Azure TTS synthesis failed: {result.reason}")
