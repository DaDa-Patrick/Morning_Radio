"""Pipeline orchestrator for MorningCast."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from ..audio.hook_finder import find_hook
from ..audio.mixer import (
    SongSegmentPlan,
    append_full_song,
    crossfade_tracks,
    duck_voice_over,
    extract_segment,
    export_with_metadata,
)
from ..data.email_parser import load_email_summary
from ..data.songs_loader import SongMetadata, load_songs
from ..data.weather import WeatherForecast, WeatherRequest, fetch_weather
from ..llm.base import OpenAIConfig
from ..llm.program_planner import plan_program
from ..llm.script_generator import generate_script
from ..llm.semantic_refiner import refine_items
from ..tts.azure_tts import AzureTTSEngine
from ..tts.base import TextToSpeechEngine
from ..tts.edge_tts_fallback import EdgeTTSEngine
from ..tts.elevenlabs_tts import ElevenLabsTTSEngine
from ..utils.logging import get_logger
from ..utils.time import timestamp_slug

logger = get_logger(__name__)


@dataclass(slots=True)
class PipelineConfig:
    date: date
    city: str
    latitude: float
    longitude: float
    email_json: Path
    songs_csv: Path
    persona_path: Optional[Path] = None
    calendar_credentials: Optional[Path] = None
    calendar_token: Optional[Path] = None
    output_dir: Path = Path("out")
    llm_api_key: Optional[str] = None
    llm_models: Dict[str, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:  # pragma: no cover - dataclass hook
        if self.llm_models is None:
            self.llm_models = {
                "refiner": "gpt-4o-mini",
                "planner": "gpt-4o",
                "script": "gpt-4o",
            }


class MorningCastPipeline:
    def __init__(self, config: PipelineConfig):
        load_dotenv()
        self.config = config
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self.persona = self._load_persona(config.persona_path)
        logger.info("Pipeline configured for %s", config.date)

    def run(self) -> Dict[str, Any]:
        logger.info("Starting MorningCast pipeline")
        email_data = load_email_summary(self.config.email_json)
        songs = load_songs(self.config.songs_csv)
        weather = self._get_weather()
        calendar_events = self._get_calendar_events()

        structured_items: List[Dict[str, Any]] = list(email_data)
        structured_items.append(
            {
                "category": "weather",
                "city": weather.city,
                "temperature_low": weather.temperature_low,
                "temperature_high": weather.temperature_high,
                "precipitation_chance": weather.precipitation_chance,
            }
        )
        for event in calendar_events:
            structured_items.append({"category": "calendar", **event})

        spoken_lines = self._run_llm_a(structured_items)
        plan_json = self._run_llm_b(spoken_lines, weather, songs, calendar_events, email_data)
        script = self._run_llm_c(plan_json)

        slug = timestamp_slug(datetime.combine(self.config.date, datetime.min.time()))
        transcript_path = self.config.output_dir / f"podcast_{slug}.md"
        transcript_path.write_text(script, encoding="utf-8")
        logger.info("Transcript saved to %s", transcript_path)

        plain_text, ssml = self._prepare_script_variants(script)
        plaintext_path = self.config.output_dir / f"podcast_{slug}.txt"
        plaintext_path.write_text(plain_text, encoding="utf-8")
        logger.info("Plain text transcript saved to %s", plaintext_path)

        timeline_path = self.config.output_dir / f"podcast_{slug}.json"
        timeline_path.write_text(json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")

        voice_path = self.config.output_dir / f"podcast_{slug}_voice.wav"
        self._render_tts(plain_text, ssml, voice_path)

        music_mix_path, final_song_path = self._build_music_mix(plan_json, songs, slug)
        ducked_path: Path
        if music_mix_path:
            ducked_path = self.config.output_dir / f"podcast_{slug}_mix.wav"
            duck_voice_over(music_mix_path, voice_path, ducked_path)
            logger.info("Voice and background bed mixed to %s", ducked_path)
        else:
            ducked_path = voice_path

        show_audio_path = ducked_path
        if final_song_path:
            appended_path = self.config.output_dir / f"podcast_{slug}_with_song.wav"
            append_full_song(ducked_path, final_song_path, appended_path)
            show_audio_path = appended_path
            logger.info("Final song appended from %s", final_song_path)

        final_audio = self.config.output_dir / f"podcast_{slug}.mp3"
        export_with_metadata(
            show_audio_path,
            final_audio,
            metadata={
                "title": f"MorningCast {self.config.date.isoformat()}",
                "artist": "MorningCast AI",
                "comment": f"Weather {weather.city} {weather.temperature_low}-{weather.temperature_high}°C",
            },
        )

        logger.info("MorningCast pipeline completed")
        return {
            "transcript_path": transcript_path,
            "plaintext_path": plaintext_path,
            "timeline_path": timeline_path,
            "audio_path": final_audio,
            "plan": plan_json,
            "script": script,
        }

    def _load_persona(self, path: Optional[Path]) -> Dict[str, Any]:
        if path and path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _get_weather(self) -> WeatherForecast:
        request = WeatherRequest(latitude=self.config.latitude, longitude=self.config.longitude, city=self.config.city)
        weather = fetch_weather(request)
        logger.info("Weather fetched: %s %s-%s", weather.city, weather.temperature_low, weather.temperature_high)
        return weather

    def _run_llm_a(self, items: List[Dict[str, Any]]) -> List[str]:
        config = OpenAIConfig(api_key=self.config.llm_api_key or os.environ.get("OPENAI_API_KEY", ""), model=self.config.llm_models["refiner"], temperature=0.6)
        lines = refine_items(items, config)
        logger.info("LLM-A produced %d spoken lines", len(lines))
        return lines

    def _run_llm_b(
        self,
        spoken_lines: List[str],
        weather: WeatherForecast,
        songs: List[SongMetadata],
        calendar_events: List[Dict[str, Any]],
        email_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        payload = {
            "spoken_lines": spoken_lines,
            "emails": email_data,
            "weather": {
                "city": weather.city,
                "temp": {"low": weather.temperature_low, "high": weather.temperature_high},
                "pop": weather.precipitation_chance,
            },
            "calendar": calendar_events,
            "songs_meta": [
                {
                    "title": song.title,
                    "artist": song.artist,
                    "path": str(song.path),
                    "bpm": song.bpm,
                    "energy": song.energy,
                }
                for song in songs
            ],
        }
        config = OpenAIConfig(api_key=self.config.llm_api_key or os.environ.get("OPENAI_API_KEY", ""), model=self.config.llm_models["planner"], temperature=0.4)
        response = plan_program(payload, config)
        response = response.strip()
        if response.startswith("```"):
            response = re.sub(r"^```[a-zA-Z0-9]*\n", "", response)
            response = re.sub(r"```$", "", response)
            response = response.strip()
        try:
            plan = json.loads(response)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM-B response: %s", response)
            raise RuntimeError("Invalid LLM-B output") from exc
        logger.info("LLM-B produced %d segments", len(plan))
        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "inputs": payload,
            "segments": plan,
        }

    def _run_llm_c(self, plan: Dict[str, Any]) -> str:
        config = OpenAIConfig(api_key=self.config.llm_api_key or os.environ.get("OPENAI_API_KEY", ""), model=self.config.llm_models["script"], temperature=0.7)
        script = generate_script(plan, self.persona, config)
        logger.info("LLM-C generated script of length %d characters", len(script))
        return script

    def _select_tts_engine(self) -> TextToSpeechEngine:
        try:
            return AzureTTSEngine()
        except Exception as exc:
            logger.warning("Azure TTS unavailable: %s", exc)
        try:
            return ElevenLabsTTSEngine()
        except Exception as exc:
            logger.warning("ElevenLabs TTS unavailable: %s", exc)
        logger.info("Falling back to Edge TTS")
        return EdgeTTSEngine()

    def _render_tts(self, plain_text: str, ssml: str, output_path: Path) -> None:
        engine = self._select_tts_engine()
        engine.synthesize(plain_text=plain_text, ssml=ssml, output_path=output_path)
        logger.info("Voice track rendered to %s", output_path)

    def _prepare_script_variants(self, script: str) -> tuple[str, str]:
        """Return a plain text version of the script and an SSML rendition."""
        script = script.strip()
        if not script:
            raise ValueError("Empty script provided for TTS")

        ssml_candidate = self._extract_ssml_block(script)
        if ssml_candidate:
            plain = self._ssml_to_plain_text(ssml_candidate)
            if not plain:
                raise ValueError("SSML block did not contain readable content")
            return plain, ssml_candidate

        plain = self._markdown_to_plain_text(script)
        if not plain:
            raise ValueError("Script did not contain any readable content")
        ssml = self._plain_text_to_ssml(plain)
        return plain, ssml

    @staticmethod
    def _extract_ssml_block(script: str) -> Optional[str]:
        """Extract an SSML block if present, removing code fences when necessary."""
        fence_match = re.search(r"```\s*(?:xml)?\s*(<speak[\s\S]+?)```", script, flags=re.IGNORECASE)
        if fence_match:
            return fence_match.group(1).strip()

        speak_match = re.search(r"(<speak[\s\S]+?</speak>)", script, flags=re.IGNORECASE)
        if speak_match:
            return speak_match.group(1).strip()
        return None

    @staticmethod
    def _ssml_to_plain_text(ssml: str) -> str:
        import html

        text = re.sub(r"<\/?speak[^>]*>", " ", ssml, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"\s+\n", "\n", text)
        text = re.sub(r"\n\s+", "\n", text)
        return html.unescape(text.strip())

    @staticmethod
    def _markdown_to_plain_text(script: str) -> str:
        import html

        text = script
        text = re.sub(r"```[\s\S]*?```", "\n", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)
        text = re.sub(r"^\s{0,3}#+\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s{0,3}(?:[-*+]\s+|\d+\.\s+)", "", text, flags=re.MULTILINE)
        text = re.sub(r"<[^>]+>", " ", text)
        lines = [line.strip() for line in text.splitlines()]

        paragraphs: List[str] = []
        current: List[str] = []
        for line in lines:
            if not line:
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
                continue
            current.append(line)
        if current:
            paragraphs.append(" ".join(current))

        cleaned = "\n\n".join(paragraphs).strip()
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        return html.unescape(cleaned)

    @staticmethod
    def _plain_text_to_ssml(plain_text: str) -> str:
        import html

        paragraphs = [para.strip() for para in re.split(r"\n\s*\n", plain_text) if para.strip()]
        if not paragraphs:
            raise ValueError("Plain text conversion produced no paragraphs")

        sentence_splitter = re.compile(r"(?<=[.!?])\s+")
        ssml_parts: List[str] = []
        for para in paragraphs:
            sentences = [html.escape(sentence.strip()) for sentence in sentence_splitter.split(para) if sentence.strip()]
            if not sentences:
                continue
            ssml_parts.append("<p>" + "".join(f"<s>{sentence}</s>" for sentence in sentences) + "</p>")

        if not ssml_parts:
            raise ValueError("Plain text sanitisation removed all readable content")

        return "<speak>" + "".join(ssml_parts) + "</speak>"

    def _build_music_mix(
        self, plan: Dict[str, Any], songs: List[SongMetadata], slug: str
    ) -> tuple[Optional[Path], Optional[Path]]:
        segments = plan.get("segments", [])
        song_sequence: List[SongMetadata] = []
        for segment in segments:
            song_title = segment.get("song")
            if not song_title:
                continue
            song = self._find_song(song_title, songs)
            if not song:
                logger.warning("Song %s not found in metadata", song_title)
                continue
            song_sequence.append(song)

        if not song_sequence:
            return None, None

        final_song = song_sequence[-1]
        final_song_path = final_song.path if final_song.path.exists() else None
        if final_song_path is None:
            logger.warning("Final song %s is missing on disk", final_song.title)

        bed_candidates = song_sequence[:-1]

        extracted_paths: List[Path] = []
        temp_dir = self.config.output_dir / "tmp"
        temp_dir.mkdir(exist_ok=True)
        for idx, song in enumerate(bed_candidates):
            hook = find_hook(song.path)
            output = temp_dir / f"segment_{idx}_{slug}.wav"
            extract_segment(
                SongSegmentPlan(source=song.path, start=max(hook.time_seconds - 15, 0), duration=45.0),
                output,
            )
            extracted_paths.append(output)

        if not extracted_paths:
            logger.info("No background music beds generated; voice will run dry.")
            return None, final_song_path

        mix_path = temp_dir / f"music_mix_{slug}.wav"
        crossfade_tracks(extracted_paths, mix_path)
        logger.info("Music mix rendered to %s", mix_path)
        return mix_path, final_song_path

    def _find_song(self, title: str, songs: List[SongMetadata]) -> Optional[SongMetadata]:
        lowered = title.lower()
        for song in songs:
            if song.title.lower() == lowered:
                return song
        return None

    def _get_calendar_events(self) -> List[Dict[str, Any]]:
        if not self.config.calendar_credentials or not self.config.calendar_credentials.exists():
            return []
        from ..data.calendar import CalendarConfig, fetch_events

        token_path = self.config.calendar_token or (self.config.calendar_credentials.parent / "token.json")
        cfg = CalendarConfig(credentials_path=self.config.calendar_credentials, token_path=token_path)
        try:
            events = fetch_events(cfg, days=1)
            logger.info("Fetched %d calendar events", len(events))
            return list(events)
        except Exception as exc:  # pragma: no cover - network I/O
            logger.warning("Calendar fetch failed: %s", exc)
            return []
