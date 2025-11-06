"""Fallback edge-tts engine."""
from __future__ import annotations

import asyncio
import html
import os
import platform
import re
import shutil
import subprocess
import unicodedata
from contextlib import suppress
from pathlib import Path
from typing import Optional

try:  # pragma: no cover - optional dependency
    from aiohttp import ClientError
except ImportError:  # pragma: no cover - fallback when aiohttp missing
    class ClientError(Exception):
        """Stub of aiohttp.ClientError when aiohttp is unavailable."""

        pass

_IMPORT_ERROR = None
try:  # pragma: no cover - optional dependency
    import edge_tts
    from edge_tts.exceptions import EdgeTTSException
except ImportError as exc:  # pragma: no cover - optional dependency
    edge_tts = None  # type: ignore
    EdgeTTSException = Exception  # type: ignore[assignment]
    _IMPORT_ERROR = exc

from ..utils.logging import get_logger
from .base import TextToSpeechEngine

logger = get_logger(__name__)


class EdgeTTSEngine(TextToSpeechEngine):  # pragma: no cover - async network call
    def __init__(self, voice: str = "zh-TW-HsiaoChenNeural"):
        self.voice = voice

    def synthesize(self, *, plain_text: str, ssml: str, output_path: Path) -> None:
        text = self._prepare_text(plain_text=plain_text, ssml=ssml)

        logger.debug("Edge TTS rendering %d characters", len(text))
        if edge_tts is None:
            if self._attempt_native_fallback(text, output_path, reason="edge-tts not installed"):
                return
            raise RuntimeError("edge-tts is not installed") from _IMPORT_ERROR  # type: ignore[name-defined]

        try:
            asyncio.run(self._synthesize(text, output_path))
        except (EdgeTTSException, ClientError, asyncio.TimeoutError, OSError) as exc:
            logger.warning("Edge TTS synthesis failed (%s); attempting native fallback", exc)
            if self._attempt_native_fallback(text, output_path, reason=str(exc)):
                return
            raise

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

    def _attempt_native_fallback(self, text: str, output_path: Path, *, reason: str) -> bool:
        """Try using a platform-native TTS tool when edge-tts fails."""

        if platform.system() != "Darwin":
            logger.error("Native fallback unavailable on this platform (reason: %s)", reason)
            return False
        say_binary = shutil.which("say")
        if not say_binary:
            logger.error("macOS 'say' command not found; cannot perform native fallback (reason: %s)", reason)
            return False

        native_voice = os.environ.get("MORNINGCAST_NATIVE_TTS_VOICE") or self._infer_native_voice()
        logger.info(
            "Falling back to macOS 'say' TTS%s",
            f" with voice '{native_voice}'" if native_voice else "",
        )
        self._synthesize_with_say(text, output_path, say_binary, native_voice=native_voice)
        return True

    def _infer_native_voice(self) -> Optional[str]:
        """Map the edge voice to an approximate macOS 'say' voice."""

        voice_key = "-".join(self.voice.split("-")[:2]).lower()
        mappings = {
            "zh-tw": "Mei-Jia",
            "en-us": "Samantha",
            "en-gb": "Serena",
        }
        return mappings.get(voice_key)

    def _synthesize_with_say(self, text: str, output_path: Path, say_binary: str, *, native_voice: Optional[str]) -> None:
        """Invoke macOS 'say' to render audio."""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with self._temporary_file(".txt", content=text) as text_file, self._temporary_file(".aiff") as raw_audio:
            command: list[str] = [
                say_binary,
                "-o",
                raw_audio,
                "-f",
                text_file,
            ]
            if native_voice:
                command[1:1] = ["-v", native_voice]
            try:
                subprocess.run(command, check=True)
            except subprocess.CalledProcessError as exc:  # pragma: no cover - system call
                raise RuntimeError("macOS 'say' command failed to synthesize speech") from exc
            self._convert_audio(Path(raw_audio), output_path)

    @staticmethod
    def _convert_audio(source: Path, target: Path) -> None:
        """Convert AIFF output into a WAV container for downstream processing."""

        try:
            import ffmpeg  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency should exist
            raise RuntimeError("ffmpeg-python is required for macOS TTS fallback conversion") from exc

        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            (
                ffmpeg.input(str(source))
                .output(str(target), ac=1, ar=44100, acodec="pcm_s16le")
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as exc:  # type: ignore[attr-defined]  # pragma: no cover - system tool error
            raise RuntimeError("Failed to convert native TTS audio with ffmpeg") from exc

    @staticmethod
    def _temporary_file(suffix: str, *, content: Optional[str] = None):
        """Yield a temporary filesystem path and clean it up afterwards."""

        class _TempFileContext:
            def __init__(self, suffix: str, payload: Optional[str]):
                self._suffix = suffix
                self._payload = payload
                self._path: Optional[Path] = None

            def __enter__(self) -> str:
                import tempfile

                fd, tmp_path = tempfile.mkstemp(prefix="morningcast_tts_", suffix=self._suffix)
                os.close(fd)
                self._path = Path(tmp_path)
                if self._payload is not None:
                    self._path.write_text(self._payload, encoding="utf-8")
                return str(self._path)

            def __exit__(self, exc_type, exc, tb) -> None:
                if self._path:
                    with suppress(OSError):
                        self._path.unlink()

        return _TempFileContext(suffix, content)
