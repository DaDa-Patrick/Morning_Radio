"""Utilities for loading preprocessed email summaries."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class EmailSummaryLoaderError(RuntimeError):
    """Raised when the email summary file cannot be parsed."""


def load_email_summary(path: str | Path) -> List[Dict[str, Any]]:
    """Load an email summary JSON document.

    Parameters
    ----------
    path:
        Location of the JSON file containing the email summaries.

    Returns
    -------
    list of dict
        The email summaries.
    """

    json_path = Path(path)
    if not json_path.exists():
        raise EmailSummaryLoaderError(f"Email summary file not found: {json_path}")

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EmailSummaryLoaderError(f"Invalid email summary JSON: {json_path}") from exc

    if not isinstance(data, list):
        raise EmailSummaryLoaderError("Expected email summary JSON to contain a list")

    return data
