"""
routes/dashboard.py – Dashboard summary endpoint.

GET /dashboard  – Returns aggregate KPI metrics, trend data, and recent detections.
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
        total_row = query_db("SELECT COUNT(*) AS cnt FROM detections", one=True)
        total_detections = total_row["cnt"] if total_row else 0

        today_row = query_db(
            "SELECT COUNT(*) AS cnt FROM detections "
            "WHERE date(created_at) = date('now')", one=True,
        )
        today_detections = today_row["cnt"] if today_row else 0

        # ── Active streams ────────────────────────────────────────────────────
        stream_row = query_db(
            "SELECT COUNT(*) AS cnt FROM streams WHERE status = 'active'", one=True,
        )
        active_streams = stream_row["cnt"] if stream_row else 0

        # ── Pending alerts ────────────────────────────────────────────────────
        alert_row = query_db(
            "SELECT COUNT(*) AS cnt FROM alerts WHERE active = 1", one=True,
        )
        pending_alerts = alert_row["cnt"] if alert_row else 0

        # ── Geo / density ─────────────────────────────────────────────────────
        hotspots      = get_geo_data(use_db=True)
        density_stats = compute_density_summary(hotspots)

        # ── LSTM trend with real history ──────────────────────────────────────
        # Pull hourly detection counts for the last 24 hours as LSTM input
        history_rows = query_db(
            "SELECT strftime('%H', created_at) AS hr, COUNT(*) AS cnt "
            "FROM detections "
            "WHERE created_at >= datetime('now', '-24 hours') "
            "GROUP BY hr ORDER BY hr",
        )
        history = [r["cnt"] for r in history_rows] if history_rows else []
        trend = predict_trend(n_points=24, base=total_detections or 580, history=history)

        # ── Recent detections list ────────────────────────────────────────────
        recent_rows = query_db(
            "SELECT id, annotated_path, labels, confidences, plastic_type, source, created_at "
            "FROM detections ORDER BY created_at DESC LIMIT 10"
        )
        recent = [dict(r) for r in recent_rows]

        # ── Plastic type breakdown ────────────────────────────────────────────
        type_rows = query_db(
            "SELECT plastic_type, COUNT(*) AS cnt FROM detections "
            "WHERE plastic_type IS NOT NULL GROUP BY plastic_type ORDER BY cnt DESC LIMIT 10"
        )
        plastic_breakdown = [dict(r) for r in type_rows] if type_rows else []

    except Exception as exc:
        return error(f"Dashboard data fetch failed: {exc}", 500)

    return success({
        "total_detections":   total_detections,
        "today_detections":   today_detections,
        "active_streams":     active_streams,
        "pending_alerts":     pending_alerts,
        "plastic_density":    density_stats,
        "trend":              trend,
        "recent_detections":  recent,
        "plastic_breakdown":  plastic_breakdown,
    })
