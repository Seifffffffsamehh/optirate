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
    
    for code, cross_rate in CROSS_RATES.items():
        existing = ExchangeHistory.query.filter_by(currency=code).all()
        existing_dates = {r.date: r for r in existing}
        
        for usd_r in usd_records:
            new_rate = round(usd_r.rate / cross_rate, 4)
            if usd_r.date in existing_dates:
                existing_dates[usd_r.date].rate = new_rate
            else:
                new_record = ExchangeHistory(currency=code, date=usd_r.date, rate=new_rate)
                db.session.add(new_record)
                
    db.session.commit()
    print("Database refined: Cross-rates calculated and missing history records inserted.")
