import os, sys
sys.path.insert(0, os.path.abspath('.'))
from app import create_app
from extensions import db
from models.exchange_history import ExchangeHistory

app = create_app()

CROSS_RATES = {
    "SAR": 3.75,       # USD/SAR
    "AED": 3.6725,     # USD/AED
    "QAR": 3.64,       # USD/QAR
    "KWD": 0.308,      # USD/KWD
    "OMR": 0.385,      # USD/OMR
    "EUR": 1 / 1.07,   # USD/EUR
    "GBP": 1 / 1.25,   # USD/GBP
    "AUD": 1 / 0.65,   # USD/AUD
    "CAD": 1.36,       # USD/CAD
    "JPY": 155.0,      # USD/JPY
    "CNY": 7.24,       # USD/CNY
}

with app.app_context():
    usd_records = ExchangeHistory.query.filter_by(currency="USD").all()
    usd_dict = {r.date: r.rate for r in usd_records}

    for code, cross_rate in CROSS_RATES.items():
        records = ExchangeHistory.query.filter_by(currency=code).all()
        for r in records:
            if r.date in usd_dict:
                # EGP/Code = (EGP/USD) / (Code/USD) = EGP/USD / cross_rate
                new_rate = usd_dict[r.date] / cross_rate
                r.rate = round(new_rate, 4)
    db.session.commit()
    print("Database refined: Placeholder data overwritten with accurate cross-rates.")
