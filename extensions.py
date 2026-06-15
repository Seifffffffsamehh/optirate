"""
Initialise Flask extensions in one place to avoid circular imports.

Extensions are instantiated here **without** binding them to a Flask app.
The application factory (``create_app`` in ``app.py``) later calls each
extension's ``init_app(app)`` method to complete the binding.

This two-phase pattern prevents circular imports that would occur if models
or routes tried to import the ``app`` object directly.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS

# ORM / database toolkit — provides ``db.Model`` base class for all models
db = SQLAlchemy()

# JWT authentication manager — handles token creation, validation, and hooks
jwt = JWTManager()

# Password hashing utility — wraps bcrypt for secure credential storage
bcrypt = Bcrypt()

# Cross-Origin Resource Sharing — configured in the app factory with allowed origins
cors = CORS()
