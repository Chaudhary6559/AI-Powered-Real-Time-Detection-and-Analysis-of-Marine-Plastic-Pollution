"""
routes/alerts.py – Alert management endpoints.

GET    /alerts           – List all alerts
POST   /set-alert        – Create or update an alert rule
DELETE /alerts/<id>      – Remove an alert
GET    /alerts/check     – Evaluate all alerts against current metrics
"""

from __future__ import annotations

from flask import Blueprint, request

from database.db import query_db, execute_db
from utils.helpers import success, error

alerts_bp = Blueprint("alerts", __name__)

VALID_METRICS = {"plastic_density", "detection_count", "stream_error_rate"}


# ── List alerts ───────────────────────────────────────────────────────────────
@alerts_bp.get("/alerts")
def list_alerts():
    rows = query_db(
        "SELECT id, name, metric, threshold, severity, active, triggered_at, created_at "
        "FROM alerts ORDER BY created_at DESC"
    )
    return success([dict(r) for r in rows])


# ── Create / update alert ─────────────────────────────────────────────────────
@alerts_bp.post("/set-alert")
def set_alert():
    """POST /set-alert – Store a new alert threshold rule."""
    body = request.get_json(silent=True) or {}

    name      = (body.get("name")     or "").strip()
    metric    = (body.get("metric")   or "").strip()
    severity  = (body.get("severity") or "warning").strip()
    threshold = body.get("threshold")

    if not name or not metric or threshold is None:
        return error("Fields 'name', 'metric', and 'threshold' are required.", 400)

    try:
        threshold = float(threshold)
    except (TypeError, ValueError):
        return error("'threshold' must be a numeric value.", 400)

    if metric not in VALID_METRICS:
        return error(
            f"Invalid metric. Choose from: {', '.join(sorted(VALID_METRICS))}.", 400
        )

    alert_id = execute_db(
        "INSERT INTO alerts (name, metric, threshold, severity, active) "
        "VALUES (?, ?, ?, ?, 1)",
        (name, metric, threshold, severity),
    )
    return success(
        {"alert_id": alert_id, "name": name, "metric": metric,
         "threshold": threshold, "severity": severity},
        201,
    )


# ── Delete alert ──────────────────────────────────────────────────────────────
@alerts_bp.delete("/alerts/<int:alert_id>")
def delete_alert(alert_id: int):
    row = query_db("SELECT id FROM alerts WHERE id = ?", (alert_id,), one=True)
    if row is None:
        return error(f"Alert {alert_id} not found.", 404)
    execute_db("DELETE FROM alerts WHERE id = ?", (alert_id,))
    return success({"deleted_alert_id": alert_id})


# ── Check / evaluate alerts ───────────────────────────────────────────────────
@alerts_bp.get("/alerts/check")
def check_alerts():
    """
    Evaluate each active alert against current DB metrics.
    Marks triggered_at if threshold is exceeded.
    """
    alerts = query_db(
        "SELECT id, name, metric, threshold, severity FROM alerts WHERE active = 1"
    )

    # Fetch current metrics once
    total_row = query_db("SELECT COUNT(*) AS cnt FROM detections", one=True)
    total_detections = total_row["cnt"] if total_row else 0

    # Average density from geo (use cached mock avg ~ 47.5 if no real data)
    from services.geo_analysis import get_geo_data, compute_density_summary
    hotspots      = get_geo_data(use_db=True)
    density_stats = compute_density_summary(hotspots)
    avg_density   = density_stats.get("average", 0.0)

    metric_values = {
        "detection_count":  total_detections,
        "plastic_density":  avg_density,
        "stream_error_rate": 0.0,   # placeholder
    }

    triggered = []
    for a in alerts:
        current_val = metric_values.get(a["metric"], 0.0)
        if current_val >= a["threshold"]:
            execute_db(
                "UPDATE alerts SET triggered_at = datetime('now') WHERE id = ?",
                (a["id"],),
            )
            triggered.append({
                "alert_id":    a["id"],
                "name":        a["name"],
                "metric":      a["metric"],
                "threshold":   a["threshold"],
                "current":     current_val,
                "severity":    a["severity"],
            })

    return success({"triggered": triggered, "checked": len(alerts)})
