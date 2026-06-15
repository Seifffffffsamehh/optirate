import os, sys
sys.path.insert(0, os.path.abspath('.'))
from app import create_app
from services.ai.ai_service import get_forecast_for_currency

app = create_app()
with app.app_context():
    currencies = ["SAR", "KWD", "USD"]
    for c in currencies:
        try:
            res = get_forecast_for_currency(c, "premium")
            print(f"--- {c} ({res['model']}) ---")
            for p in res.get('predictions', []):
                print(f"{p['date']}: {p['expected']}")
        except Exception as e:
            print(f"{c}: ERROR {e}")
