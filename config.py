"""Configuration, kept separate from application code (NFR-06)."""
import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # SECRET_KEY must come from the environment for anything beyond local demo.
    # If it is missing, a random per-process key is used (sessions then reset on
    # every restart) instead of a hardcoded secret.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DATABASE = os.environ.get("DATABASE") or os.path.join(BASE_DIR, "instance", "inventory.db")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set SESSION_COOKIE_SECURE=1 when serving over HTTPS.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE") == "1"
    SECRET_KEY_FROM_ENV = bool(os.environ.get("SECRET_KEY"))
