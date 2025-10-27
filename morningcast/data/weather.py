"""Fetch daily weather information using the Open-Meteo API."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional

import requests

DEFAULT_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass(slots=True)
class WeatherRequest:
    latitude: float
    longitude: float
    city: str
    timezone: str = "Asia/Taipei"


@dataclass(slots=True)
class WeatherForecast:
    city: str
    date: date
    temperature_low: float
    temperature_high: float
    precipitation_chance: Optional[float]
    raw: Dict[str, Any]


def fetch_weather(req: WeatherRequest) -> WeatherForecast:
    """Fetch weather data for today using the Open-Meteo API."""

    params = {
        "latitude": req.latitude,
        "longitude": req.longitude,
        "timezone": req.timezone,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_probability_mean"],
    }

    response = requests.get(DEFAULT_OPEN_METEO_URL, params=params, timeout=10)
    response.raise_for_status()

    payload = response.json()
    daily = payload.get("daily", {})
    temperatures_max = daily.get("temperature_2m_max", [None])
    temperatures_min = daily.get("temperature_2m_min", [None])
    precipitation = daily.get("precipitation_probability_mean", [None])

    forecast = WeatherForecast(
        city=req.city,
        date=date.today(),
        temperature_low=float(temperatures_min[0]) if temperatures_min[0] is not None else float("nan"),
        temperature_high=float(temperatures_max[0]) if temperatures_max[0] is not None else float("nan"),
        precipitation_chance=float(precipitation[0]) if precipitation[0] is not None else None,
        raw=payload,
    )

    return forecast
