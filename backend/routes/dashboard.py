"""
routes/dashboard.py – Dashboard summary endpoint.

GET /dashboard
  Returns aggregate metrics for the UI dashboard cards:
    - total_detections, today_detections
    - plastic_density (kg/km² average)
    - active_streams
    - pending_alerts
    - trend data (from LSTM mock)
"""

from __future__ import annotations

from flask import Blueprint

from database.db import query_db
from services.geo_analysis import get_geo_data, compute_density_summary
from models.lstm import predict_trend
from utils.helpers import success, error

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/dashboard")
def dashboard():
    """GET /dashboard – Return all dashboard KPI metrics."""

    try:
        # ── Detections ────────────────────────────────────────────────────────
        total_row = query_db(
            "SELECT COUNT(*) AS cnt FROM detections", one=True
        )
        total_detections = total_row["cnt"] if total_row else 0

        today_row = query_db(
            "SELECT COUNT(*) AS cnt FROM detections "
            "WHERE date(created_at) = date('now')",
            one=True,
        )
        today_detections = today_row["cnt"] if today_row else 0

        # ── Active streams ────────────────────────────────────────────────────
        stream_row = query_db(
            "SELECT COUNT(*) AS cnt FROM streams WHERE status = 'active'",
            one=True,
        )
        active_streams = stream_row["cnt"] if stream_row else 0

        # ── Pending / triggered alerts ────────────────────────────────────────
        alert_row = query_db(
            "SELECT COUNT(*) AS cnt FROM alerts WHERE active = 1",
            one=True,
        )
        pending_alerts = alert_row["cnt"] if alert_row else 0

        # ── Geo / density ─────────────────────────────────────────────────────
        hotspots      = get_geo_data(use_db=True)
        density_stats = compute_density_summary(hotspots)

        # ── Trend data (LSTM mock) ────────────────────────────────────────────
        trend = predict_trend(n_points=24, base=total_detections or 580)

        # ── Recent detections list ────────────────────────────────────────────
        recent_rows = query_db(
            "SELECT id, annotated_path, plastic_type, source, created_at "
            "FROM detections ORDER BY created_at DESC LIMIT 5"
        )
        recent = [dict(r) for r in recent_rows]

    except Exception as exc:
        return error(f"Dashboard data fetch failed: {exc}", 500)

    return success({
        "total_detections":  total_detections,
        "today_detections":  today_detections,
        "active_streams":    active_streams,
        "pending_alerts":    pending_alerts,
        "plastic_density":   density_stats,
        "trend":             trend,
        "recent_detections": recent,
    })
