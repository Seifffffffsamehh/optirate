import os, sys
from datetime import datetime
sys.path.insert(0, os.path.abspath('.'))
from app import create_app
from extensions import db
from models.exchange_history import ExchangeHistory

app = create_app()

def process_usd():
    with app.app_context():
        with open('raw1.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        count = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 4:
                date_str = parts[0]
                sell_rate_str = parts[3]
                
                try:
                    # Convert DD/MM/YYYY to YYYY-MM-DD
                    dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                    rate = float(sell_rate_str)
                    
                    # Check if exists
                    record = ExchangeHistory.query.filter_by(currency="USD", date=dt).first()
                    if not record:
                        record = ExchangeHistory(currency="USD", date=dt, rate=rate)
                        db.session.add(record)
                    else:
                        record.rate = rate
                    count += 1
                except Exception as e:
                    print(f"Error parsing {line}: {e}")
        
        db.session.commit()
        print(f"Successfully processed {count} USD records.")

if __name__ == "__main__":
    process_usd()
