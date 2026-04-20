"""
routes/streams.py – Video stream management endpoints.

POST /start-stream   – Register and start a new video stream (threaded)
POST /stop-stream    – Stop a running stream by stream_id
GET  /streams        – List all streams with their current status
"""

from __future__ import annotations

import threading
from pathlib import Path

import cv2
from flask import Blueprint, request, current_app

from database.db import query_db, execute_db
from services.detection import run_detection
from utils.helpers import success, error

streams_bp = Blueprint("streams", __name__)

# Registry of active stream threads  { stream_id: threading.Event }
_stop_events: dict[int, threading.Event] = {}


def _process_stream(app, stream_id: int, url: str, stop_event: threading.Event) -> None:
    """Background thread: read frames, run detection periodically, save results."""
    frame_interval = app.config.get("STREAM_FRAME_INTERVAL", 30)
    annotated_dir  = Path(app.static_folder) / "annotated"
    conf           = app.config.get("YOLO_CONF_THRESHOLD", 0.30)

    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        with app.app_context():
            execute_db(
                "UPDATE streams SET status = 'error' WHERE id = ?", (stream_id,)
            )
        return

    frame_count = 0
    with app.app_context():
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1
            if frame_count % frame_interval != 0:
                continue

            # Save frame as temp file for the pipeline
            tmp_path = Path(app.config["UPLOAD_FOLDER"]) / f"stream_{stream_id}_frame.jpg"
            cv2.imwrite(str(tmp_path), frame)

            try:
                run_detection(
                    image_path    = tmp_path,
                    annotated_dir = annotated_dir,
                    conf_threshold= conf,
                    save_to_db    = True,
                    stream_id     = stream_id,
                    source        = "stream",
                )
            except Exception:
                pass  # keep running on individual frame errors

        cap.release()
        execute_db(
            "UPDATE streams SET status = 'stopped', stopped_at = datetime('now') WHERE id = ?",
            (stream_id,),
        )


# ── Start stream ──────────────────────────────────────────────────────────────
@streams_bp.post("/start-stream")
def start_stream():
    """POST /start-stream – Register a new stream and begin processing."""
    body  = request.get_json(silent=True) or {}
    url   = (body.get("url") or "").strip()
    label = (body.get("label") or "Unnamed Stream").strip()

    if not url:
        return error("Stream 'url' is required (RTSP/RTMP/HTTP).", 400)

    # Persist stream record
    stream_id = execute_db(
        "INSERT INTO streams (url, label, status, started_at) "
        "VALUES (?, ?, 'active', datetime('now'))",
        (url, label),
    )

    # Launch background thread
    stop_event = threading.Event()
    _stop_events[stream_id] = stop_event

    app = current_app._get_current_object()   # real app, not proxy
    t = threading.Thread(
        target    = _process_stream,
        args      = (app, stream_id, url, stop_event),
        daemon    = True,
        name      = f"stream-{stream_id}",
    )
    t.start()

    return success({"stream_id": stream_id, "url": url, "label": label, "status": "active"}, 201)


# ── Stop stream ───────────────────────────────────────────────────────────────
@streams_bp.post("/stop-stream")
def stop_stream():
    """POST /stop-stream – Signal a running stream to stop."""
    body      = request.get_json(silent=True) or {}
    stream_id = body.get("stream_id")

    if not stream_id:
        return error("'stream_id' is required.", 400)

    event = _stop_events.get(int(stream_id))
    if event:
        event.set()
        _stop_events.pop(int(stream_id), None)
    else:
        # May have already stopped; update DB anyway
        execute_db(
            "UPDATE streams SET status = 'stopped', stopped_at = datetime('now') WHERE id = ?",
            (int(stream_id),),
        )

    return success({"stream_id": stream_id, "status": "stopped"})


# ── List streams ──────────────────────────────────────────────────────────────
@streams_bp.get("/streams")
def list_streams():
    """GET /streams – Return all streams with status."""
    rows = query_db(
        "SELECT id, url, label, status, started_at, stopped_at, created_at "
        "FROM streams ORDER BY created_at DESC"
    )
    return success([dict(r) for r in rows])
