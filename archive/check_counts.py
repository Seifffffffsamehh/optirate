import os, sys
sys.path.insert(0, os.path.abspath('.'))
from app import create_app
from models.exchange_history import ExchangeHistory

app = create_app()
with app.app_context():
    count = ExchangeHistory.query.count()
    print(f"Total records in DB: {count}")
    currencies = ExchangeHistory.query.with_entities(ExchangeHistory.currency).distinct().all()
    for c in currencies:
        c_count = ExchangeHistory.query.filter_by(currency=c[0]).count()
        print(f"{c[0]}: {c_count} records")
