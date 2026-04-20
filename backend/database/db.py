"""
database/db.py – SQLite connection helpers for Abyssal Lens.
Uses Flask's application context (g) to reuse a single connection per request.
"""

import sqlite3
from pathlib import Path

import flask
from flask import current_app, g


def get_db() -> sqlite3.Connection:
    """Return a per-request SQLite connection (creates one on first call)."""
    if "db" not in g:
        db_path: Path = current_app.config["DB_PATH"]
        db_path.parent.mkdir(parents=True, exist_ok=True)

        g.db = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row  # dict-like access: row["column"]
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None) -> None:
    """Close the DB connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app: flask.Flask) -> None:
    """
    Initialise the database — execute schema.sql.
    Called once from app factory; safe to call multiple times (CREATE IF NOT EXISTS).
    """
    schema_path: Path = app.config["SCHEMA_PATH"]
    db_path: Path = app.config["DB_PATH"]
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        conn = sqlite3.connect(str(db_path))
        with open(schema_path, "r", encoding="utf-8") as fh:
            conn.executescript(fh.read())
        conn.commit()
        conn.close()
    print(f"[DB] Database initialised → {db_path}")


def query_db(query: str, args=(), one: bool = False):
    """
    Convenience helper for SELECT queries.
    Returns a single Row if *one=True*, else a list of Rows.
    """
    cur = get_db().execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(query: str, args=()) -> int:
    """
    Convenience helper for INSERT / UPDATE / DELETE.
    Returns the lastrowid of the executed statement.
    """
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur.lastrowid
