"""
routes/reports.py – Report generation endpoint.

GET /generate-report
  Generates a CSV (always) and optional PDF summary of all detections.
  Files saved to static/reports/. Returns download URLs.

Query params:
  ?fmt=csv|pdf|both  (default: both)
"""

from __future__ import annotations

from flask import Blueprint, request

from services.report_generator import generate_csv, generate_pdf
from utils.helpers import success, error

reports_bp = Blueprint("reports", __name__)


@reports_bp.get("/generate-report")
def generate_report():
    """GET /generate-report – Build and return report download paths."""
    fmt = request.args.get("fmt", "both").lower()

    if fmt not in ("csv", "pdf", "both"):
        return error("Invalid 'fmt'. Choose: csv, pdf, or both.", 400)

    result: dict = {}

    try:
        if fmt in ("csv", "both"):
            result["csv"] = generate_csv()

        if fmt in ("pdf", "both"):
            result["pdf"] = generate_pdf()
    except Exception as exc:
        return error(f"Report generation failed: {exc}", 500)

    return success(result)
