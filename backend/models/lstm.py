"""
models/lstm.py – LSTM trend predictor for detection time-series.

For the FYP demo this is a pure mock: it generates a realistic-looking
detection count trend using a random-walk, matching the shape expected
by the dashboard chart.
"""

from __future__ import annotations

import math
import random
from typing import List


def predict_trend(n_points: int = 24, base: int = 580) -> List[dict]:
    """
    Generate *n_points* synthetic detection count values.

    In a real deployment this would feed `n_points` historical observations
    into an LSTM and return the model's stepped predictions.

    Args:
        n_points: number of time-step data points to return (default 24 = 24 h).
        base: approximate baseline detection count per hour.

    Returns:
        List of {"hour": str, "count": int, "density": float}
    """
    data = []
    count = base
    for i in range(n_points):
        # Gentle sinusoidal trend + Gaussian noise
        sinusoidal_mod = math.sin(math.pi * i / 12) * 60
        noise = random.gauss(0, 25)
        count = max(0, int(count + sinusoidal_mod + noise))

        hour_label = f"{i:02d}:00"
        density = round(count * 0.0032 + random.uniform(-0.5, 0.5), 2)  # kg/km²

        data.append({
            "hour": hour_label,
            "count": count,
            "density": max(0.0, density),
        })
    return data
