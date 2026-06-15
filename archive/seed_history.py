import os, sys, random
from datetime import date, timedelta
sys.path.insert(0, os.path.abspath('.'))
from app import create_app
from extensions import db
from models.exchange_history import ExchangeHistory

app = create_app()

CURRENCIES = {"EUR": 54.0, "GBP": 64.0, "SAR": 13.0, "AED": 13.5, "KWD": 150.0, "QAR": 13.1, "OMR": 124.0, "CNY": 6.8, "JPY": 0.33, "CAD": 36.0, "AUD": 31.0}

with app.app_context():
    for code, base_rate in CURRENCIES.items():
        existing = db.session.query(ExchangeHistory).filter_by(currency=code).count()
        if existing < 90:
            for i in range(90):
                d = date.today() - timedelta(days=90 - i)
                rate = base_rate + random.uniform(-0.5, 0.5)
                record = ExchangeHistory(currency=code, date=d, rate=rate)
                db.session.add(record)
    db.session.commit()
    print("Seeded historical data.")
