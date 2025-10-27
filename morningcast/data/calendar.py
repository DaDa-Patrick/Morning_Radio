"""Google Calendar data fetcher."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Sequence

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except Exception:  # pragma: no cover - optional dependency
    Request = None  # type: ignore
    Credentials = None  # type: ignore
    InstalledAppFlow = None  # type: ignore
    build = None  # type: ignore

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


@dataclass(slots=True)
class CalendarConfig:
    credentials_path: Path
    token_path: Path


def _load_credentials(cfg: CalendarConfig) -> Any:
    creds = None
    if cfg.token_path.exists() and Credentials is not None:
        creds = Credentials.from_authorized_user_file(str(cfg.token_path), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        if Request is None:
            raise RuntimeError("google.auth Request is not available")
        creds.refresh(Request())
        return creds
    if InstalledAppFlow is None:
        raise RuntimeError("Google API client libraries are not fully installed")
    flow = InstalledAppFlow.from_client_secrets_file(str(cfg.credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)
    cfg.token_path.write_text(creds.to_json())
    return creds


def fetch_events(cfg: CalendarConfig, days: int = 1) -> List[Dict[str, Any]]:
    """Fetch upcoming events for the next ``days`` days."""
    if build is None or Credentials is None:
        raise RuntimeError("Google Calendar dependencies missing")

    creds = _load_credentials(cfg)

    service = build("calendar", "v3", credentials=creds)
    now = datetime.utcnow().isoformat() + "Z"
    end_time = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
    events_result = (
        service.events()  # type: ignore[attr-defined]
        .list(calendarId="primary", timeMin=now, timeMax=end_time, singleEvents=True, orderBy="startTime")
        .execute()
    )
    events: Sequence[Dict[str, Any]] = events_result.get("items", [])
    formatted: List[Dict[str, Any]] = []
    for event in events:
        formatted.append(
            {
                "title": event.get("summary", "(no title)"),
                "start": event.get("start", {}).get("dateTime", event.get("start", {}).get("date")),
                "end": event.get("end", {}).get("dateTime", event.get("end", {}).get("date")),
                "location": event.get("location"),
            }
        )
    return formatted
