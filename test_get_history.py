from app import create_app
from services.engine.history_engine import get_history
import logging

logging.basicConfig(level=logging.DEBUG)

app = create_app()
with app.app_context():
    print(get_history("USD", limit=5))
