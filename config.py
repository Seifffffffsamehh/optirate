"""Application configuration loaded from environment variables."""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    # ── Flask ──
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-dev-secret")

    # ── Database ──
    _db_user = os.getenv("DB_USER", "root")
    _db_pass = os.getenv("DB_PASSWORD", "")
    _db_host = os.getenv("DB_HOST", "localhost")
    _db_port = os.getenv("DB_PORT", "3306")
    _db_name = os.getenv("DB_NAME", "optirate_db")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{_db_user}:{_db_pass}"
        f"@{_db_host}:{_db_port}/{_db_name}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── JWT ──
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-dev-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
