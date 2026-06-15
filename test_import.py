import traceback
try:
    import pandas as pd
    print("pandas ok")
    from services.ai.prophet_model import generate_forecast
    print("prophet ok")
except Exception as e:
    traceback.print_exc()
