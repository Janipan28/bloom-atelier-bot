import asyncio
import sqlite3
import os
from bot.config import get_settings

async def upgrade_db():
    settings = get_settings()
    # Extract path from sqlite+aiosqlite:///./flower_bot.sqlite3
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    if db_path.startswith("./"):
        db_path = os.path.join(os.getcwd(), db_path[2:])
    
    print(f"Upgrading database at {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Update customers table
    try:
        cursor.execute("ALTER TABLE customers ADD COLUMN balance INTEGER DEFAULT 0")
        print("Added 'balance' to 'customers'")
    except sqlite3.OperationalError:
        print("'balance' already exists in 'customers'")
        
    try:
        cursor.execute("ALTER TABLE customers ADD COLUMN tags TEXT")
        print("Added 'tags' to 'customers'")
    except sqlite3.OperationalError:
        print("'tags' already exists in 'customers'")

    # 2. Update orders table
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN points_used INTEGER DEFAULT 0")
        print("Added 'points_used' to 'orders'")
    except sqlite3.OperationalError:
        print("'points_used' already exists in 'orders'")
        
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN discount_amount INTEGER DEFAULT 0")
        print("Added 'discount_amount' to 'orders'")
    except sqlite3.OperationalError:
        print("'discount_amount' already exists in 'orders'")
        
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN final_amount INTEGER")
        print("Added 'final_amount' to 'orders'")
    except sqlite3.OperationalError:
        print("'final_amount' already exists in 'orders'")
        
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT")
        print("Added 'payment_method' to 'orders'")
    except sqlite3.OperationalError:
        print("'payment_method' already exists in 'orders'")

    # 3. Update promo_codes table
    try:
        cursor.execute("ALTER TABLE promo_codes ADD COLUMN discount_type TEXT DEFAULT 'percent'")
        print("Added 'discount_type' to 'promo_codes'")
    except sqlite3.OperationalError:
        print("'discount_type' already exists in 'promo_codes'")
        
    try:
        cursor.execute("ALTER TABLE promo_codes ADD COLUMN min_order_amount INTEGER DEFAULT 0")
        print("Added 'min_order_amount' to 'promo_codes'")
    except sqlite3.OperationalError:
        print("'min_order_amount' already exists in 'promo_codes'")

    # 4. Create admin_users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id BIGINT NOT NULL,
        full_name TEXT,
        role TEXT DEFAULT 'florist',
        is_active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(telegram_id)
    )
    """)
    print("Created 'admin_users' table if not exists")

    conn.commit()
    conn.close()
    print("Database upgrade complete.")

if __name__ == "__main__":
    asyncio.run(upgrade_db())
