"""
app.py – Abyssal Lens Flask application factory.

Registers all blueprints, initialises the database, loads ML models,
and starts the Flask dev server when executed directly.
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from database.db import init_db, close_db

# ── Import model loaders ──────────────────────────────────────────────────────
from models import yolo as yolo_model
from models import resnet as resnet_model

# ── Import route blueprints ───────────────────────────────────────────────────
from routes.auth import auth_bp
from routes.image import image_bp
from routes.streams import streams_bp
from routes.dashboard import dashboard_bp
from routes.geo import geo_bp
from routes.reports import reports_bp
from routes.alerts import alerts_bp


def create_app(config_class: type = Config) -> Flask:
    """Application factory – create and configure the Flask app."""

    app = Flask(
        __name__,
        static_folder=str(Config.STATIC_FOLDER),
        static_url_path="/static",
    )

    # ── Load configuration ────────────────────────────────────────────────────
    app.config.from_object(config_class)
    # Allow Path objects alongside strings in config
    app.config["UPLOAD_FOLDER"] = str(Config.UPLOAD_FOLDER)
    app.config["DB_PATH"]       = Config.DB_PATH
    app.config["SCHEMA_PATH"]   = Config.SCHEMA_PATH
    app.config["SECRET_KEY"]    = Config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

    # ── CORS (allow HTML frontend on any origin during dev) ───────────────────
    CORS(app, resources={r"/*": {"origins": Config.CORS_ORIGINS}})

    # ── Database ──────────────────────────────────────────────────────────────
    init_db(app)
    app.teardown_appcontext(close_db)

    # ── ML Model Loading (non-blocking – fallback mock if missing) ────────────
    yolo_model.load_model(Config.YOLO_MODEL_PATH)
    resnet_model.load_model(Config.RESNET_MODEL_PATH)

    # ── Register Blueprints ───────────────────────────────────────────────────
    app.register_blueprint(auth_bp,      url_prefix="/auth")
    app.register_blueprint(image_bp)                          # /analyze
    app.register_blueprint(streams_bp)                        # /start-stream, /stop-stream
    app.register_blueprint(dashboard_bp)                      # /dashboard
    app.register_blueprint(geo_bp)                            # /geo-data
    app.register_blueprint(reports_bp)                        # /generate-report
    app.register_blueprint(alerts_bp)                         # /alerts

    # ── Health-check endpoint ─────────────────────────────────────────────────
    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "app": "Abyssal Lens"})

    # ── Global error handlers ─────────────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"status": "error", "message": str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"status": "error", "message": "Endpoint not found."}), 404

    @app.errorhandler(413)
    def payload_too_large(e):
        return jsonify({"status": "error", "message": "File exceeds the 16 MB limit."}), 413

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"status": "error", "message": "Internal server error."}), 500

    return app


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 5000)),
        debug=Config.DEBUG,
        use_reloader=False,   # Disable reloader to avoid double model-load
    )
