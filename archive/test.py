import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from services.engine.currency_engine import get_currency_rates

rates = get_currency_rates(role="admin")
currencies = set(r.get('currency', 'NONE') for r in rates)
print(f"Fetched {len(rates)} rows. Currencies: {currencies}")
