"""User model with role-based enum."""

from extensions import db


class User(db.Model):
    """Represents a platform user."""

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

    def to_dict(self):
        """Return a JSON-safe representation (never expose password)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
        }

    def __repr__(self):
        return f"<User {self.username}>"
