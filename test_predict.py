import os, sys
sys.path.insert(0, os.path.abspath('.'))
from app import create_app
from services.ai.ai_service import get_forecast_for_currency

app = create_app()
with app.app_context():
    print("Testing USD forecast:")
    try:
        res = get_forecast_for_currency("USD", "premium")
        print(res)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    print("\nTesting SAR forecast:")
    try:
        res = get_forecast_for_currency("SAR", "premium")
        print(res)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
