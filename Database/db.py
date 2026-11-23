"""Request-scoped SQLite connection helper."""
import os
import sqlite3

from flask import current_app, g


def _connect(path):
    # isolation_level=None -> autocommit; transactions are explicit (BEGIN/COMMIT).
    conn = sqlite3.connect(path, isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # NFR-05: on every connection
    return conn


def get_db():
    if "db" not in g:
        g.db = _connect(current_app.config["DATABASE"])
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables from schema.sql. Safe to re-run (IF NOT EXISTS); never drops data."""
    path = current_app.config["DATABASE"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    schema = os.path.join(os.path.dirname(__file__), "schema.sql")
    conn = _connect(path)
    try:
        with open(schema, encoding="utf-8") as f:
            conn.executescript(f.read())
    finally:
        conn.close()


def init_app(app):
    app.teardown_appcontext(close_db)
