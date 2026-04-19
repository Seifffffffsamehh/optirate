"""OptiRate — Phase 1 Entry Point (Authentication System)."""

import json

from flask import Flask, jsonify
from config import Config
from extensions import db, jwt, bcrypt, cors


def create_app():
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # ── Initialise extensions ────────────────────────────────────────────
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # ── JWT identity serialisation (sub must be a string) ────────────────
    @jwt.user_identity_loader
    def user_identity_lookup(identity):
        """Serialize dict identity → JSON string for the JWT 'sub' claim."""
        if isinstance(identity, dict):
            return json.dumps(identity)
        return str(identity)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        """Deserialize the 'sub' claim back to a dict for current_user."""
        sub = jwt_data["sub"]
        try:
            return json.loads(sub)
        except (json.JSONDecodeError, TypeError):
            return sub

    # ── Register blueprints ──────────────────────────────────────────────
    from routes.auth import auth_bp, protected_bp
    from routes.health import health_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(protected_bp)
    app.register_blueprint(health_bp)

    # ── Global error handlers ────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed."}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error."}), 500

    # ── JWT custom error responses ───────────────────────────────────────
    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"error": "Authorization token is missing.", "detail": reason}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"error": "Invalid token.", "detail": reason}), 401

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired."}), 401

    # ── Create tables ────────────────────────────────────────────────────
    with app.app_context():
        from models.user import User  # noqa: F401 — ensure model is registered
        db.create_all()

    return app


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=True)
