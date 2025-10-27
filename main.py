from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from morningcast.pipeline.orchestrator import MorningCastPipeline, PipelineConfig
from morningcast.utils.logging import configure_logging


DEFAULT_LAT = 25.0330
DEFAULT_LON = 121.5654


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MorningCast generator")
    parser.add_argument("--date", default="today", help="Production date (YYYY-MM-DD or 'today')")
    parser.add_argument("--city", default="Taipei", help="City name")
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT, help="Latitude")
    parser.add_argument("--lon", type=float, default=DEFAULT_LON, help="Longitude")
    parser.add_argument("--emails", type=Path, default=Path("email_summary.json"), help="Path to email summary JSON")
    parser.add_argument("--songs", type=Path, default=Path("songs.csv"), help="Path to songs metadata CSV")
    parser.add_argument("--persona", type=Path, default=Path("persona.json"), help="Persona JSON file")
    parser.add_argument("--output", type=Path, default=Path("out"), help="Output directory")
    parser.add_argument("--calendar-credentials", type=Path, default=Path("credentials.json"), help="Google Calendar credentials.json")
    parser.add_argument("--calendar-token", type=Path, default=Path("token.json"), help="Google Calendar token storage")
    parser.add_argument("--llm-key", dest="llm_key", default=None, help="OpenAI API key override")
    parser.add_argument("--model-refiner", default=None, help="Override model for LLM-A")
    parser.add_argument("--model-planner", default=None, help="Override model for LLM-B")
    parser.add_argument("--model-script", default=None, help="Override model for LLM-C")
    return parser.parse_args()


def parse_date(value: str) -> date:
    if value == "today":
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    configure_logging()
    args = parse_args()
    production_date = parse_date(args.date)
    models = {}
    if args.model_refiner:
        models["refiner"] = args.model_refiner
    if args.model_planner:
        models["planner"] = args.model_planner
    if args.model_script:
        models["script"] = args.model_script
    pipeline = MorningCastPipeline(
        PipelineConfig(
            date=production_date,
            city=args.city,
            latitude=args.lat,
            longitude=args.lon,
            email_json=args.emails,
            songs_csv=args.songs,
            persona_path=args.persona if args.persona.exists() else None,
            calendar_credentials=args.calendar_credentials if args.calendar_credentials.exists() else None,
            calendar_token=args.calendar_token if args.calendar_token.exists() else None,
            output_dir=args.output,
            llm_api_key=args.llm_key,
            llm_models=models or None,
        )
    )
    pipeline.run()


if __name__ == "__main__":
    main()
