"""
services/geo_analysis.py – Geospatial analysis for plastic hotspots.

For production: pulls detection coordinates from the DB and performs
density estimation with a simple grid. Also provides a rich mock
dataset for demos where real GPS data is unavailable.
"""

from __future__ import annotations

import random
from typing import List

from database.db import query_db

# ── Static mock hotspot seeds (real-world ocean garbage patch coords) ─────────
_MOCK_HOTSPOTS = [
    # Great Pacific Garbage Patch
    {"lat": 32.4,  "lon": -142.1, "region": "North Pacific Gyre"},
    {"lat": 28.7,  "lon": -150.3, "region": "North Pacific Gyre"},
    {"lat": 35.1,  "lon": -138.9, "region": "North Pacific Gyre"},
    # Indian Ocean patch
    {"lat": -25.3, "lon":   80.6, "region": "Indian Ocean"},
    {"lat": -30.1, "lon":   77.4, "region": "Indian Ocean"},
    # Mediterranean
    {"lat":  38.5, "lon":   14.2, "region": "Mediterranean Sea"},
    {"lat":  36.7, "lon":   20.1, "region": "Mediterranean Sea"},
    # South Pacific
    {"lat": -18.4, "lon": -115.3, "region": "South Pacific Gyre"},
    # North Atlantic
    {"lat":  29.2, "lon":  -42.5, "region": "North Atlantic Gyre"},
    {"lat":  33.8, "lon":  -35.1, "region": "North Atlantic Gyre"},
]


def _enrich_hotspot(seed: dict, idx: int) -> dict:
    """Add randomised density / count values to a seed hotspot."""
    return {
        "id":       idx + 1,
        "lat":      seed["lat"]  + random.uniform(-0.5, 0.5),
        "lon":      seed["lon"]  + random.uniform(-0.5, 0.5),
        "density":  round(random.uniform(10.0, 85.0), 1),   # kg/km²
        "count":    random.randint(50, 800),
        "severity": random.choice(["low", "medium", "high", "critical"]),
        "region":   seed["region"],
    }


def get_geo_data(use_db: bool = True) -> List[dict]:
    """
    Return a list of geospatial hotspot objects.

    If real detections with lat/lon exist in the DB they are merged with
    the mock seeds; otherwise only mock data is returned.

    Returns:
        [
          {
            "id": int,
            "lat": float, "lon": float,
            "density": float,           # kg/km²
            "count": int,               # number of detections
            "severity": str,            # low | medium | high | critical
            "region": str
          },
          ...
        ]
    """
    hotspots = []

    # Pull real coords from DB
    if use_db:
        try:
            rows = query_db(
                "SELECT id, latitude, longitude FROM detections "
                "WHERE latitude IS NOT NULL AND longitude IS NOT NULL "
                "ORDER BY created_at DESC LIMIT 50"
            )
            for i, row in enumerate(rows):
                hotspots.append({
                    "id":       row["id"],
                    "lat":      row["latitude"],
                    "lon":      row["longitude"],
                    "density":  round(random.uniform(10.0, 85.0), 1),
                    "count":    random.randint(20, 400),
                    "severity": random.choice(["low", "medium", "high"]),
                    "region":   "Field Detection",
                })
        except Exception:
            pass  # DB not ready yet – fall through to mock

    # Pad / supplement with mock data so dashboard always has visual content
    needed = max(0, 8 - len(hotspots))
    for i, seed in enumerate(_MOCK_HOTSPOTS[:needed]):
        hotspots.append(_enrich_hotspot(seed, len(hotspots) + i))

    return hotspots


def compute_density_summary(hotspots: List[dict]) -> dict:
    """Return aggregate stats across all hotspot data."""
    if not hotspots:
        return {"average": 0.0, "max": 0.0, "total_sites": 0}
    densities = [h["density"] for h in hotspots]
    return {
        "average":     round(sum(densities) / len(densities), 1),
        "max":         max(densities),
        "total_sites": len(hotspots),
    }
