from app import create_app
from services.ai.ai_service import get_strategic_recommendation

app = create_app()
with app.app_context():
    print(get_strategic_recommendation("USD", 1000, "buy", "admin"))
