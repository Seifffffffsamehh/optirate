"""
Logging models for AI predictions and recommendations.

These lightweight audit tables record every invocation of the premium AI
endpoints (``/api/v3/predict`` and ``/api/v3/recommend``).  The admin
dashboard reads from these tables to display "predictions today" and
"recommendations today" counts, enabling usage monitoring and capacity
planning without adding overhead to the AI pipeline itself.
"""

from extensions import db
from datetime import datetime


class PredictionLog(db.Model):
    """Tracks each AI prediction request.

    Fields:
        id (int): Auto-incrementing primary key.
        currency (str): The currency code that was forecasted (e.g. ``"USD"``).
        timestamp (datetime): UTC time of the request.  Indexed for efficient
            date-range queries on the admin dashboard.
    """
    __tablename__ = "prediction_logs"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    currency = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class RecommendationLog(db.Model):
    """Tracks each AI recommendation request.

    Fields:
        id (int): Auto-incrementing primary key.
        currency (str): The currency code involved (e.g. ``"EUR"``).
        action (str): The user-requested action — ``"buy"`` or ``"sell"``.
        timestamp (datetime): UTC time of the request.  Indexed for efficient
            date-range queries on the admin dashboard.
    """
    __tablename__ = "recommendation_logs"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    currency = db.Column(db.String(10), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
