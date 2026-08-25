import sqlite3
from datetime import datetime, timedelta

DB_PATH = "report.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_report_data(days=7):
    conn = get_connection()

    # Total number of orders
    total_orders = conn.execute(
        "SELECT COUNT(*) AS count FROM orders"
    ).fetchone()["count"]

    # Total revenue
    total_revenue = conn.execute(
        "SELECT SUM(amount) AS total FROM orders"
    ).fetchone()["total"]

    # Top 5 products by revenue
    top_products_rows = conn.execute("""
        SELECT product, SUM(amount) AS revenue
        FROM orders
        GROUP BY product
        ORDER BY revenue DESC
        LIMIT 5
    """).fetchall()
    top_products = [
        {"product": row["product"], "revenue": round(row["revenue"], 2)}
        for row in top_products_rows
    ]

    # Orders per day for the last N days (parameterized)
    since_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    daily_rows = conn.execute("""
        SELECT created_at AS day, COUNT(*) AS count
        FROM orders
        WHERE created_at >= ?
        GROUP BY created_at
        ORDER BY created_at ASC
    """, (since_date,)).fetchall()
    orders_per_day = [
        {"day": row["day"], "count": row["count"]}
        for row in daily_rows
    ]

    conn.close()

    return {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "top_products": top_products,
        "orders_per_day": orders_per_day,
        "days_window": days,
    }


if __name__ == "__main__":
    import json
    data = get_report_data()
    print(json.dumps(data, indent=2))