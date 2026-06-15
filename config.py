"""
Application configuration loaded from environment variables.

All sensitive values (DB credentials, JWT secret) are read from a ``.env`` file
via ``python-dotenv``.  Fallback defaults are provided for local development so
the app can start without an env file, but **must** be overridden in production.
"""

import os
import ssl
from datetime import timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Load .env file from the project root into os.environ
load_dotenv()


def _build_database_uri() -> str:
    """Assemble a SQLAlchemy MySQL URI from env vars (URL-encodes credentials)."""
    explicit = os.getenv("DATABASE_URI")
    if explicit:
        return explicit

    user = quote_plus(os.getenv("DB_USER", "root"))
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "optirate_db")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"


def _build_engine_options() -> dict:
    """Connection pool + optional TLS for cloud MySQL (e.g. Aiven)."""
    options = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }
    if os.getenv("DB_SSL", "false").lower() in ("1", "true", "required", "yes"):
        options["connect_args"] = {"ssl": ssl.create_default_context()}
    return options


class Config:
    """Base configuration consumed by ``app.config.from_object(Config)``.

    Attributes:
        SECRET_KEY: Flask's general-purpose secret (session signing, etc.).
        SQLALCHEMY_DATABASE_URI: Full MySQL connection string assembled from
            individual DB_* environment variables.
        SQLALCHEMY_TRACK_MODIFICATIONS: Disabled to save memory — the event
            system is not used by the app.
        JWT_SECRET_KEY: HMAC key used to sign and verify JWT access tokens.
        JWT_ACCESS_TOKEN_EXPIRES: Token lifetime; currently set to 1 hour.
    """

    # ── Flask ──
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-dev-secret")

    # ── Database ──
    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _build_engine_options()

    # ── CORS (only needed if frontend is on a different origin) ──
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")

    # ── JWT ──
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-dev-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
