"""
routes/reports.py – Report generation endpoint.

GET /generate-report?fmt=csv|pdf|both
POST /generate-report   (same as GET, for fetch compatibility)
GET  /reports-list      – List previously generated report files
"""

from __future__ import annotations

from flask import Blueprint, request, send_file
from pathlib import Path

from services.report_generator import generate_csv, generate_pdf
from config import Config
from utils.helpers import success, error

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/generate-report", methods=["GET", "POST"])
def generate_report():
    """Generate and return report download paths."""
    fmt = (request.args.get("fmt") or (request.get_json(silent=True) or {}).get("fmt") or "both").lower()

    if fmt not in ("csv", "pdf", "both"):
        return error("Invalid 'fmt'. Choose: csv, pdf, or both.", 400)

    result: dict = {}

    try:
        if fmt in ("csv", "both"):
            result["csv"] = generate_csv()
            result["csv_url"] = "/" + result["csv"]

        if fmt in ("pdf", "both"):
            result["pdf"] = generate_pdf()
            result["pdf_url"] = "/" + result["pdf"]
    except Exception as exc:
        return error(f"Report generation failed: {exc}", 500)

    return success(result)


@reports_bp.get("/reports-list")
def reports_list():
    """GET /reports-list – List available report files."""
    reports_dir = Config.REPORTS_FOLDER
    if not reports_dir.exists():
        return success([])

    files = []
    for f in sorted(reports_dir.iterdir(), reverse=True):
        if f.suffix in (".csv", ".pdf"):
            files.append({
                "name":     f.name,
                "url":      f"/static/reports/{f.name}",
                "size_kb":  round(f.stat().st_size / 1024, 1),
                "type":     f.suffix.lstrip("."),
            })
    return success(files[:50])
