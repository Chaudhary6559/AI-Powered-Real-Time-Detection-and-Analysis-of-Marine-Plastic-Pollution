-- Abyssal Lens – SQLite Database Schema
-- Run once via db.init_db() or manually: sqlite3 marine.db < schema.sql

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────
-- USERS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'analyst',   -- admin | analyst | scientist
    created_at    DATETIME DEFAULT (datetime('now'))
);

-- Seed a default admin account (password: admin123  →  bcrypt hash placeholder)
-- Replace with a real hash before deployment.
INSERT OR IGNORE INTO users (username, email, password_hash, role)
VALUES (
    'admin',
    'admin@marine-intel.org',
    'pbkdf2:sha256:600000$abyssallens$placeholder_hash_replace_me',
    'admin'
);

-- ─────────────────────────────────────────────
-- DETECTIONS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS detections (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path     TEXT,
    annotated_path TEXT,
    labels         TEXT    DEFAULT '[]',     -- JSON array of label strings
    confidences    TEXT    DEFAULT '[]',     -- JSON array of float scores
    bboxes         TEXT    DEFAULT '[]',     -- JSON array of [x1,y1,x2,y2] lists
    plastic_type   TEXT,                     -- dominant classification result
    latitude       REAL,
    longitude      REAL,
    source         TEXT    DEFAULT 'upload', -- upload | stream
    stream_id      INTEGER REFERENCES streams(id) ON DELETE SET NULL,
    created_at     DATETIME DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────
-- ALERTS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    metric       TEXT    NOT NULL,           -- e.g. plastic_density | detection_count
    threshold    REAL    NOT NULL,
    severity     TEXT    NOT NULL DEFAULT 'warning',  -- info | warning | critical
    active       INTEGER NOT NULL DEFAULT 1,          -- 1 = enabled
    triggered_at DATETIME,
    created_at   DATETIME DEFAULT (datetime('now'))
);

-- Seed a sample alert
INSERT OR IGNORE INTO alerts (id, name, metric, threshold, severity)
VALUES (1, 'High Plastic Density', 'plastic_density', 50.0, 'critical');

-- ─────────────────────────────────────────────
-- STREAMS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS streams (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    url        TEXT    NOT NULL,
    label      TEXT    DEFAULT 'Unnamed Stream',
    status     TEXT    NOT NULL DEFAULT 'stopped',  -- active | stopped | error
    started_at DATETIME,
    stopped_at DATETIME,
    created_at DATETIME DEFAULT (datetime('now'))
);
