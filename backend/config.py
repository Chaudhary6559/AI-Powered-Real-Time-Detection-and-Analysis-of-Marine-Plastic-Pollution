"""
config.py – Centralised configuration for Abyssal Lens Flask backend.
All environment-specific values live here so the rest of the codebase stays portable.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    # ── Flask ────────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "abyssal-lens-dev-secret-change-in-prod")
    DEBUG = os.environ.get("DEBUG", "true").lower() == "true"

    # ── File Uploads ─────────────────────────────────────────────────────────
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    STATIC_FOLDER = BASE_DIR / "static"
    REPORTS_FOLDER = BASE_DIR / "static" / "reports"
    ANNOTATED_FOLDER = BASE_DIR / "static" / "annotated"

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB hard limit
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}

    # ── Database ─────────────────────────────────────────────────────────────
    DB_PATH = BASE_DIR / "database" / "marine.db"
    SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"

    # ── ML Model Paths ───────────────────────────────────────────────────────
    YOLO_MODEL_PATH = BASE_DIR / "models" / "yolo_model.pt"
    RESNET_MODEL_PATH = BASE_DIR / "models" / "cnn_classifier.h5"

    # ── Detection Parameters ─────────────────────────────────────────────────
    YOLO_CONF_THRESHOLD = 0.30   # minimum confidence to keep a box
    IMG_SIZE = 640               # YOLO input resolution

    # ── Session / Auth ───────────────────────────────────────────────────────
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Allow the HTML frontend (file:// or any localhost port) to reach the API
    CORS_ORIGINS = ["*"]

    # ── Video Stream ─────────────────────────────────────────────────────────
    STREAM_FRAME_INTERVAL = 30   # process every N-th frame to reduce CPU load


# Create required directories on import (safe – no-op if already exist)
for _dir in [
    Config.UPLOAD_FOLDER,
    Config.REPORTS_FOLDER,
    Config.ANNOTATED_FOLDER,
]:
    _dir.mkdir(parents=True, exist_ok=True)
