"""Song hook finder based on onset strength."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import librosa
import numpy as np


@dataclass(slots=True)
class HookResult:
    time_seconds: float
    strength: float


DEFAULT_RANGE: Tuple[float, float] = (45.0, 75.0)


def find_hook(path: str | Path, search_range: Tuple[float, float] = DEFAULT_RANGE) -> HookResult:
    y, sr = librosa.load(path, mono=True)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    times = librosa.times_like(onset_env, sr=sr)
    mask = (times >= search_range[0]) & (times <= search_range[1])
    if not np.any(mask):
        index = int(np.argmax(onset_env))
    else:
        index = int(np.argmax(onset_env[mask]))
        offset = np.arange(len(onset_env))[mask][0]
        index += offset
    return HookResult(time_seconds=float(times[index]), strength=float(onset_env[index]))
