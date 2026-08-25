import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "report.db"

PRODUCTS = ["Widget", "Gadget", "Gizmo", "Doohickey", "Thingamajig", "Contraption"]
CUSTOMERS = [
    "Alice Johnson", "Bob Smith", "Carla Diaz", "David Lee", "Emma Wilson",
    "Frank Chen", "Grace Kim", "Henry Patel", "Isabel Rossi", "Jack Nguyen"
]

def get_connection():
    return sqlite3.connect(DB_PATH)

def create_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT NOT NULL,
            product TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()

def seed(conn, count=200):
    # Delete all rows first so running this twice doesn't double the data
    conn.execute("DELETE FROM orders")
    conn.commit()

    now = datetime.now()
    rows = []
    for _ in range(count):
        customer = random.choice(CUSTOMERS)
        product = random.choice(PRODUCTS)
        amount = round(random.uniform(5, 200), 2)
        days_ago = random.randint(0, 29)
        created_at = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        rows.append((customer, product, amount, created_at))

    conn.executemany(
        "INSERT INTO orders (customer, product, amount, created_at) VALUES (?, ?, ?, ?)",
        rows
    )
    conn.commit()

if __name__ == "__main__":
    conn = get_connection()
    create_table(conn)
    seed(conn, 200)

    count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    print(f"Seeded database. Row count: {count}")
    conn.close()