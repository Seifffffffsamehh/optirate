"""
OptiRate — Entry Point (Phase 1 Auth + Phase 2 Financial Data).

This module defines the Flask application factory and bootstraps all core
components of the OptiRate platform, including:

- Flask extensions (SQLAlchemy, JWT, Bcrypt, CORS)
- Blueprint registration for auth, health, v2/v3 API, and admin routes
- JWT identity serialization/deserialization for embedding user metadata
- Seed user creation for development and testing
- APScheduler-based background job for daily exchange-rate ingestion
- Global subscription guard middleware that auto-downgrades expired premiums
"""

import json

from flask import Flask, jsonify, request
from config import Config
from extensions import db, jwt, bcrypt, cors
import threading
import time
from services.engine.history_engine import sync_daily_history


def _seed_users(app):
    """Create default test accounts if they don't already exist.

    Seeds three accounts (admin, premium, free) so the application always has
    a baseline set of users for development/testing.  Existing accounts with
    matching emails are silently skipped to make the function idempotent.

    Args:
        app: The Flask application instance (needed for the app context and logger).
    """
    from models.user import User

    seed_accounts = [
        {"username": "admin",   "email": "admin@test.com",   "password": "123456", "role": "admin"},
        {"username": "premium", "email": "premium@test.com", "password": "123456", "role": "premium"},
        {"username": "free",    "email": "free@test.com",    "password": "123456", "role": "free"},
    ]

    with app.app_context():
        for acct in seed_accounts:
            if User.query.filter_by(email=acct["email"]).first():
                continue
            hashed_pw = bcrypt.generate_password_hash(acct["password"]).decode("utf-8")
            user = User(
                username=acct["username"],
                email=acct["email"],
                password=hashed_pw,
                role=acct["role"],
            )
            db.session.add(user)
            app.logger.info("Seeded user: %s (%s)", acct["email"], acct["role"])
        db.session.commit()


def create_app():
    """Application factory — creates and configures the Flask app.

    This factory pattern allows multiple app instances (e.g. for testing) and
    keeps configuration, extensions, and blueprints neatly scoped.

    Returns:
        Flask: A fully configured Flask application ready to serve requests.
    """
    import os
    base_dir = os.path.abspath(os.path.dirname(__file__))
    # Serve the frontend SPA from the FRONTEND directory as static files
    frontend_dir = os.path.join(base_dir, "FRONTEND")
    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    app.config.from_object(Config)

    # ── Initialise extensions ────────────────────────────────────────────
    # Extensions are instantiated in extensions.py to avoid circular imports;
    # here we bind them to this specific app instance.
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)

    # CORS — restrict to the frontend dev server(s) and local static server.
    # Origins are read from config (comma-separated string) with sensible defaults.
    default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"
    allowed_origins = [
        o.strip() for o in app.config.get("CORS_ORIGINS", default_origins).split(",")
    ]
    cors.init_app(app, resources={r"/api/*": {"origins": allowed_origins}})

    # ── JWT identity serialisation (sub must be a string) ────────────────
    # Flask-JWT-Extended requires the JWT "sub" claim to be a string.
    # We embed a dict of user metadata (id, username, role, plan) as a
    # JSON-encoded string so downstream handlers can recover the full identity.

    @jwt.user_identity_loader
    def user_identity_lookup(identity):
        """Serialize dict identity → JSON string for the JWT 'sub' claim.

        If the identity is already a plain value (e.g. int), it is cast to str.
        """
        if isinstance(identity, dict):
            return json.dumps(identity)
        return str(identity)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        """Deserialize the 'sub' claim back to a dict for current_user.

        Falls back to the raw sub value if JSON parsing fails (defensive).
        """
        sub = jwt_data["sub"]
        try:
            return json.loads(sub)
        except (json.JSONDecodeError, TypeError):
            return sub

    # ── Register blueprints ──────────────────────────────────────────────
    # Order matters only when url_prefix collisions exist; these are distinct.
    from routes.auth import auth_bp, protected_bp
    from routes.health import health_bp
    from routes.v2 import v2_bp
    from routes.v3 import v3_bp
    from routes.admin import admin_bp, admin_public_bp

    app.register_blueprint(auth_bp)          # /api/auth/*
    app.register_blueprint(protected_bp)     # /api/protected, /api/me
    app.register_blueprint(health_bp)        # /api/health
    app.register_blueprint(v2_bp)            # /api/v2/*   — public financial data
    app.register_blueprint(v3_bp)            # /api/v3/*   — premium AI features
    app.register_blueprint(admin_bp)         # /api/v1/admin/*
    app.register_blueprint(admin_public_bp)  # /api/admin/* (public alias)

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    # ── Global error handlers (unified schema) ───────────────────────────
    # Every error response follows {"status": "error", "message": "..."} to
    # give the frontend a consistent contract.

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"status": "error", "message": "Resource not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"status": "error", "message": "Method not allowed."}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"status": "error", "message": "Internal server error."}), 500

    # ── JWT custom error responses (unified schema) ──────────────────────
    # Override default Flask-JWT-Extended error bodies to match our schema.

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"status": "error", "message": "Authorization token is missing."}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"status": "error", "message": "Invalid token."}), 401

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({"status": "error", "message": "Token has expired."}), 401

    # ── Create tables & seed ─────────────────────────────────────────────
    # Import all models so SQLAlchemy registers their tables, then create
    # any missing tables (idempotent — existing tables are left untouched).
    with app.app_context():
        from models.user import User  # noqa: F401 — ensure model is registered
        from models.exchange_history import ExchangeHistory  # noqa: F401
        from models.logs import PredictionLog, RecommendationLog # noqa: F401
        db.create_all()

    _seed_users(app)

    # ── Background Daily Sync ────────────────────────────────────────────
    # APScheduler runs a background thread that scrapes CBE exchange rates
    # daily at 10:00 AM UTC and also fires once at startup so fresh data is
    # available immediately after deployment.
    from apscheduler.schedulers.background import BackgroundScheduler
    
    def run_daily_sync_job():
        """Wrapper that catches exceptions so APScheduler keeps running."""
        try:
            sync_daily_history(app)
        except Exception as e:
            app.logger.error(f"Daily history sync failed: {e}")

    scheduler = BackgroundScheduler()
    # Run scraper at least once per day (e.g., every day at 10:00 AM)
    # Using interval for now or cron. Let's use cron for once per day.
    scheduler.add_job(func=run_daily_sync_job, trigger="cron", hour=10, minute=0)
    
    # Also run once at startup to ensure we have today's data right away
    scheduler.add_job(func=run_daily_sync_job, trigger="date")
    
    scheduler.start()
    app.logger.info("APScheduler started for daily history sync.")

    # ── Global Subscription Guard ────────────────────────────────────────
    # Runs before every API request. If a premium user's subscription has
    # expired, their plan and role are silently reverted to "free" so they
    # lose access to premium-only endpoints on the very next request.
    @app.before_request
    def subscription_guard():
        """Auto-downgrade expired premium subscriptions on every request."""
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        from models.user import User
        from datetime import datetime

        # Only check on API routes that require auth
        if not request.path.startswith("/api/"):
            return
        try:
            verify_jwt_in_request(optional=True)
            raw = get_jwt_identity()
            if not raw:
                return
            identity = json.loads(raw) if isinstance(raw, str) else raw
            uid = identity.get("id")
            if not uid:
                return
            user = User.query.get(uid)
            # Downgrade if the subscription expiry date has passed
            if user and user.plan == "premium" and user.subscription_expires:
                if datetime.utcnow() > user.subscription_expires:
                    user.plan = "free"
                    user.role = "free"
                    user.subscription_expires = None
                    db.session.commit()
                    app.logger.info(
                        "Subscription Guard: Auto-downgraded user %s.", user.username
                    )
        except Exception:
            pass  # Don't block requests if guard fails

    return app



# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=True)
