"""Phase 3.3 Migration: Add plan and subscription_expires columns to users table."""
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

conn = pymysql.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "optirate_db"),
)

cursor = conn.cursor()

# Add plan column if it doesn't exist
try:
    cursor.execute("ALTER TABLE users ADD COLUMN plan VARCHAR(20) NOT NULL DEFAULT 'free'")
    print("✓ Added 'plan' column.")
except pymysql.err.OperationalError as e:
    if "Duplicate column" in str(e):
        print("- 'plan' column already exists.")
    else:
        raise

# Add subscription_expires column if it doesn't exist
try:
    cursor.execute("ALTER TABLE users ADD COLUMN subscription_expires DATETIME NULL")
    print("✓ Added 'subscription_expires' column.")
except pymysql.err.OperationalError as e:
    if "Duplicate column" in str(e):
        print("- 'subscription_expires' column already exists.")
    else:
        raise

# Add index on plan column
try:
    cursor.execute("CREATE INDEX idx_users_plan ON users(plan)")
    print("✓ Added index on 'plan' column.")
except pymysql.err.OperationalError as e:
    if "Duplicate key name" in str(e):
        print("- Index on 'plan' already exists.")
    else:
        raise

# Sync existing roles: set plan = role for existing users
cursor.execute("UPDATE users SET plan = role WHERE plan = 'free' AND role != 'free'")
updated = cursor.rowcount
print(f"✓ Synced plan field for {updated} existing user(s).")

conn.commit()
cursor.close()
conn.close()
print("\n✅ Phase 3.3 database migration complete!")
