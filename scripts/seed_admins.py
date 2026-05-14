import asyncio
import sqlite3
import os
from bot.config import get_settings

async def seed_admins():
    settings = get_settings()
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    if db_path.startswith("./"):
        db_path = os.path.join(os.getcwd(), db_path[2:])
    
    print(f"Seeding admins in database at {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    admin_ids = settings.admin_id_set
    for admin_id in admin_ids:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO admin_users (telegram_id, role, is_active) VALUES (?, ?, ?)",
                (admin_id, "manager", 1)
            )
            print(f"Seeded admin {admin_id} as manager")
        except Exception as e:
            print(f"Error seeding admin {admin_id}: {e}")

    conn.commit()
    conn.close()
    print("Admin seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_admins())
