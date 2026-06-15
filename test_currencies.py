from app import create_app
from services.engine.currency_engine import get_currency_rates

app = create_app()
with app.app_context():
    print(get_currency_rates(role="admin"))
