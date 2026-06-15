import os, sys
sys.path.insert(0, os.path.abspath('.'))
from app import create_app
from models.exchange_history import ExchangeHistory

app = create_app()
with app.app_context():
    records = ExchangeHistory.query.filter_by(currency="USD").order_by(ExchangeHistory.date.desc()).limit(10).all()
    print("USD records:")
    for r in records:
        print(f"{r.date}: {r.rate}")
