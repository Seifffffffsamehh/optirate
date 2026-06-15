from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE exchange_history ADD COLUMN source VARCHAR(50) DEFAULT 'CBE'"))
        db.session.commit()
        print("Column 'source' added.")
    except Exception as e:
        print("Column may already exist:", e)
