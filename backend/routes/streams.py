"""
routes/streams.py – Video stream management endpoints.

POST /start-stream   – Register + start an RTSP/RTMP/HTTP stream (threaded)
POST /stop-stream    – Stop a running stream
GET  /streams        – List all streams with status
POST /analyze-frame  – Analyze a single webcam frame (base64 or multipart)
GET  /stream-feed    – SSE: push latest detection event for a stream
"""

from __future__ import annotations

import base64
import io
import threading
import uuid
from pathlib import Path

import cv2
import numpy as np
from flask import Blueprint, request, current_app, Response

from database.db import query_db, execute_db
from services.detection import run_detection
from utils.helpers import success, error

streams_bp = Blueprint("streams", __name__)

# Registry of active stream threads  { stream_id: threading.Event }
_stop_events: dict[int, threading.Event] = {}
# Latest detection event per stream (for SSE)
_latest_events: dict[int, dict] = {}


def _process_stream(app, stream_id: int, url: str, stop_event: threading.Event) -> None:
    """Background thread: read frames, run detection periodically, save results."""
    frame_interval = app.config.get("STREAM_FRAME_INTERVAL", 30)
    annotated_dir  = Path(app.static_folder) / "annotated"
    conf           = app.config.get("YOLO_CONF_THRESHOLD", 0.30)

    # Support numeric index for webcam (e.g. url="0" or "1")
    source = int(url) if url.isdigit() else url
    cap = cv2.VideoCapture(source)
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

            tmp_path = Path(app.config["UPLOAD_FOLDER"]) / f"stream_{stream_id}_frame.jpg"
            cv2.imwrite(str(tmp_path), frame)

            try:
                result = run_detection(
                    image_path    = tmp_path,
                    annotated_dir = annotated_dir,
                    conf_threshold= conf,
                    save_to_db    = True,
                    stream_id     = stream_id,
                    source        = "stream",
                )
                _latest_events[stream_id] = result
            except Exception:
                pass

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
        return error("Stream 'url' is required (RTSP/RTMP/HTTP or webcam index '0').", 400)

    stream_id = execute_db(
        "INSERT INTO streams (url, label, status, started_at) "
        "VALUES (?, ?, 'active', datetime('now'))",
        (url, label),
    )

    stop_event = threading.Event()
    _stop_events[stream_id] = stop_event

    app = current_app._get_current_object()
    t = threading.Thread(
        target = _process_stream,
        args   = (app, stream_id, url, stop_event),
        daemon = True,
        name   = f"stream-{stream_id}",
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
        execute_db(
            "UPDATE streams SET status = 'stopped', stopped_at = datetime('now') WHERE id = ?",
            (int(stream_id),),
        )

    _latest_events.pop(int(stream_id), None)
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


# ── Single-frame webcam analysis ──────────────────────────────────────────────
@streams_bp.post("/analyze-frame")
def analyze_frame():
    """
    POST /analyze-frame – Analyze a single webcam frame.

    Accepts multipart 'file' field OR JSON {"frame": "<base64 jpeg>"}
    Returns detection result JSON.
    """
    annotated_dir = Path(current_app.static_folder) / "annotated"
    conf          = current_app.config.get("YOLO_CONF_THRESHOLD", 0.30)
    upload_dir    = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    img_np = None

    # ── Accept multipart file ─────────────────────────────────────────────────
    if "file" in request.files:
        file = request.files["file"]
        buf  = np.frombuffer(file.read(), dtype=np.uint8)
        img_np = cv2.imdecode(buf, cv2.IMREAD_COLOR)

    # ── Accept JSON base64 ────────────────────────────────────────────────────
    elif request.is_json:
        body   = request.get_json(silent=True) or {}
        b64    = body.get("frame", "")
        if not b64:
            return error("JSON body must contain 'frame' (base64 JPEG).", 400)
        # Strip optional data-URL prefix
        if "," in b64:
            b64 = b64.split(",", 1)[1]
        try:
            raw    = base64.b64decode(b64)
            buf    = np.frombuffer(raw, dtype=np.uint8)
            img_np = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        except Exception as exc:
            return error(f"Failed to decode frame: {exc}", 400)

    if img_np is None:
        return error("No frame provided. Use multipart 'file' or JSON 'frame' field.", 400)

    # Save to temp file for the pipeline
    tmp_name = f"webcam_{uuid.uuid4().hex[:8]}.jpg"
    tmp_path = upload_dir / tmp_name
    cv2.imwrite(str(tmp_path), img_np)

    try:
        result = run_detection(
            image_path    = tmp_path,
            annotated_dir = annotated_dir,
            conf_threshold= conf,
            save_to_db    = True,
            source        = "webcam",
        )
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        return error(f"Detection failed: {exc}", 500)

    return success(result, 200)


# ── SSE latest detection event ────────────────────────────────────────────────
@streams_bp.get("/stream-event/<int:stream_id>")
def stream_event(stream_id: int):
    """GET /stream-event/<id> – Return the latest detection for a stream."""
    event = _latest_events.get(stream_id)
    if event is None:
        return success({"stream_id": stream_id, "status": "no_event_yet"})
    return success(event)
