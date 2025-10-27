from __future__ import annotations

from datetime import datetime


def timestamp_slug(target: datetime) -> str:
    return target.strftime("%Y%m%d")
