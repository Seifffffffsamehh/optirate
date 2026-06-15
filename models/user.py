"""
User model with role-based enum and subscription management.

Defines the ``users`` table which stores account credentials, role-based
access control, and premium subscription state for every registered user.
"""

from extensions import db


class User(db.Model):
    """Represents a platform user.

    Fields:
        id (int): Auto-incrementing primary key.
        username (str): Unique display name (3–80 chars, indexed for fast lookup).
        email (str): Unique email address (indexed, used as an alternate login key).
        password (str): Bcrypt-hashed password — never exposed via ``to_dict()``.
        role (enum): Access-control tier — ``"free"``, ``"premium"``, or ``"admin"``.
            Determines which API endpoints and data the user may access.
        plan (str): Subscription plan label (``"free"`` or ``"premium"``).
            Kept in sync with ``role`` by the admin and upgrade endpoints.
        subscription_expires (datetime | None): UTC expiry timestamp for premium
            subscriptions.  ``None`` means no active subscription.  The global
            subscription guard and ``premium_required`` decorator auto-downgrade
            users once this date passes.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum("free", "premium", "admin", name="user_role"),
        nullable=False,
        default="free",
        server_default="free",
    )
    # Phase 3.3: Subscription management columns
    plan = db.Column(db.String(20), nullable=False, default="free", server_default="free", index=True)
    subscription_expires = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        """Return a JSON-safe representation (never expose password).

        Returns:
            dict: User fields suitable for API responses.  The
            ``subscription_expires`` value is ISO-formatted when present.
        """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "plan": self.plan,
            "subscription_expires": self.subscription_expires.isoformat() if self.subscription_expires else None,
        }

    def __repr__(self):
        return f"<User {self.username}>"
