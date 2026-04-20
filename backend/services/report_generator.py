"""
services/report_generator.py – CSV and PDF report generation.

Pulls detections from the database, writes a CSV to static/reports/,
and builds a simple PDF summary with ReportLab.

Both functions return a URL-friendly relative path, e.g.:
  "static/reports/detections_20260413_155900.csv"
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path

from flask import current_app

from database.db import query_db

# ── Resolve reports directory ─────────────────────────────────────────────────
def _reports_dir() -> Path:
    p = Path(current_app.static_folder) / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


# ─────────────────────────────────────────────────────────────────────────────
# CSV
# ─────────────────────────────────────────────────────────────────────────────
def generate_csv() -> str:
    """
    Generate a CSV file from all detections in the database.
    Returns the relative path (e.g., 'static/reports/detections_….csv').
    """
    rows = query_db(
        "SELECT id, image_path, annotated_path, labels, confidences, "
        "bboxes, plastic_type, latitude, longitude, source, stream_id, created_at "
        "FROM detections ORDER BY created_at DESC"
    )

    filename = f"detections_{_timestamp()}.csv"
    filepath = _reports_dir() / filename

    with open(filepath, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "ID", "Image Path", "Annotated Path", "Labels", "Confidences",
            "Bboxes", "Plastic Type", "Latitude", "Longitude",
            "Source", "Stream ID", "Created At",
        ])
        for r in rows:
            writer.writerow([
                r["id"],
                r["image_path"],
                r["annotated_path"],
                r["labels"],
                r["confidences"],
                r["bboxes"],
                r["plastic_type"],
                r["latitude"],
                r["longitude"],
                r["source"],
                r["stream_id"],
                r["created_at"],
            ])

    return f"static/reports/{filename}"


# ─────────────────────────────────────────────────────────────────────────────
# PDF
# ─────────────────────────────────────────────────────────────────────────────
def generate_pdf() -> str:
    """
    Generate a concise PDF summary report using ReportLab.
    Returns the relative path (e.g., 'static/reports/report_….pdf').
    Falls back gracefully if ReportLab is not installed.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer,
            Table, TableStyle,
        )
        from reportlab.lib import colors
    except ImportError:
        raise RuntimeError(
            "reportlab is not installed. Install it via: pip install reportlab"
        )

    filename = f"report_{_timestamp()}.pdf"
    filepath = _reports_dir() / filename

    doc    = SimpleDocTemplate(str(filepath), pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    # ── Title ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("Abyssal Lens – Marine Plastic Detection Report", styles["Title"]))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.6*cm))

    # ── Summary stats ─────────────────────────────────────────────────────────
    total_row  = query_db("SELECT COUNT(*) AS cnt FROM detections", one=True)
    total      = total_row["cnt"] if total_row else 0
    stream_row = query_db(
        "SELECT COUNT(*) AS cnt FROM streams WHERE status = 'active'", one=True
    )
    active_streams = stream_row["cnt"] if stream_row else 0

    story.append(Paragraph("Summary", styles["Heading2"]))
    summary_data = [
        ["Metric",          "Value"],
        ["Total Detections",  str(total)],
        ["Active Streams",    str(active_streams)],
        ["Report Format",     "PDF (auto-generated)"],
    ]
    t = Table(summary_data, colWidths=[9*cm, 6*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003d66")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#eaf4fb"), colors.white]),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING",    (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.6*cm))

    # ── Recent detections table ───────────────────────────────────────────────
    rows = query_db(
        "SELECT id, plastic_type, source, created_at FROM detections "
        "ORDER BY created_at DESC LIMIT 20"
    )
    story.append(Paragraph("Recent Detections (last 20)", styles["Heading2"]))

    table_data = [["ID", "Plastic Type", "Source", "Timestamp"]]
    for r in rows:
        table_data.append([
            str(r["id"]),
            r["plastic_type"] or "—",
            r["source"] or "upload",
            r["created_at"] or "—",
        ])

    if len(table_data) > 1:
        dt = Table(table_data, colWidths=[2*cm, 5.5*cm, 3.5*cm, 5.5*cm])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003d66")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#eaf4fb"), colors.white]),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("PADDING",    (0, 0), (-1, -1), 4),
        ]))
        story.append(dt)
    else:
        story.append(Paragraph("No detections recorded yet.", styles["Normal"]))

    doc.build(story)
    return f"static/reports/{filename}"
