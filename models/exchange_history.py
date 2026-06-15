"""
ExchangeHistory model for storing historical currency rates.

Each row represents a single day's exchange rate for a given currency, scraped
from the Central Bank of Egypt (CBE).  The daily sync job
(``services.engine.history_engine.sync_daily_history``) populates this table
via APScheduler, and the data serves as training input for Prophet-based
AI predictions in the V3 API.
"""

from extensions import db


class ExchangeHistory(db.Model):
    """Stores historical exchange rate records from CBE.

    Fields:
        id (int): Auto-incrementing primary key.
        currency (str): ISO currency code (e.g. ``"USD"``, ``"EUR"``) or
            metal code (``"GOLD"``, ``"SILVER"``).  Indexed for fast filtering.
        date (date): The calendar date of the rate snapshot.  Indexed for
            chronological queries.
        rate (float): The exchange rate (or metal price) on that date.
        source (str): Data provenance label — defaults to ``"CBE"``.

    Constraints:
        A unique constraint on ``(currency, date)`` prevents duplicate entries
        for the same asset on the same day, making the sync job safely
        idempotent (re-runs won't create duplicates).
    """

    __tablename__ = "exchange_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    currency = db.Column(db.String(10), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    rate = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(50), nullable=False, default="CBE")

    # Prevent duplicate entries for the same currency + date
    __table_args__ = (
        db.UniqueConstraint("currency", "date", name="uq_currency_date"),
    )

    def to_dict(self):
        """Return a JSON-safe representation.

        Returns:
            dict: All fields with the date formatted as an ISO string.
        """
        return {
            "id": self.id,
            "currency": self.currency,
            "date": self.date.isoformat(),
            "rate": self.rate,
            "source": self.source,
        }

    def __repr__(self):
        return f"<ExchangeHistory {self.currency} {self.date} {self.rate} {self.source}>"
