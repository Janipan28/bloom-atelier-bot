import sqlite3

def migrate():
    conn = sqlite3.connect('flower_bot.sqlite3')
    cursor = conn.cursor()
    
    # Add is_loyalty_credited to orders if not exists
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN is_loyalty_credited BOOLEAN DEFAULT 0")
        print("Added is_loyalty_credited to orders")
    except sqlite3.OperationalError:
        print("is_loyalty_credited already exists in orders")
        
    # Ensure loyalty_points is in customers
    try:
        cursor.execute("ALTER TABLE customers ADD COLUMN loyalty_points INTEGER DEFAULT 0")
        print("Added loyalty_points to customers")
    except sqlite3.OperationalError:
        print("loyalty_points already exists in customers")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
