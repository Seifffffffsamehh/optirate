"""
Application configuration loaded from environment variables.

All sensitive values (DB credentials, JWT secret) are read from a ``.env`` file
via ``python-dotenv``.  Fallback defaults are provided for local development so
the app can start without an env file, but **must** be overridden in production.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file from the project root into os.environ
load_dotenv()


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
    # Individual components allow easy per-environment overrides (e.g. in CI).
    _db_user = os.getenv("DB_USER", "root")
    _db_pass = os.getenv("DB_PASSWORD", "")
    _db_host = os.getenv("DB_HOST", "localhost")
    _db_port = os.getenv("DB_PORT", "3306")
    _db_name = os.getenv("DB_NAME", "optirate_db")

    # Assembled MySQL URI using PyMySQL as the DBAPI driver
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URI",
        f"mysql+pymysql://{_db_user}:{_db_pass}@{_db_host}:{_db_port}/{_db_name}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── JWT ──
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-dev-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
