import asyncio
import datetime
import math
import os
import random
import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse
from jinja2 import Template
from playwright.sync_api import sync_playwright

DB_FILE = "report.db"
REPORTS_DIR = "reports"

os.makedirs(REPORTS_DIR, exist_ok=True)

app = FastAPI(title="PDF Report Generator")


# ==========================================
# Database Initialization & Seeding
# ==========================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT NOT NULL,
                product TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at DATE NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS generated_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date DATE UNIQUE NOT NULL,
                file_path TEXT NOT NULL,
                total_orders INTEGER NOT NULL,
                total_revenue REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def seed_db():
    products = ["Laptop", "Mouse", "Keyboard", "Monitor", "Headphones", "Webcam"]
    customers = [f"Customer {i}" for i in range(1, 25)]
    today = datetime.date.today()
    
    with get_db() as conn:
        conn.execute("DELETE FROM orders")  # Ensures idempotent seeding
        
        orders = []
        for _ in range(200):
            cust = random.choice(customers)
            prod = random.choice(products)
            amt = round(random.uniform(5.0, 200.0), 2)
            days_ago = random.randint(0, 29)
            order_date = (today - datetime.timedelta(days=days_ago)).isoformat()
            orders.append((cust, prod, amt, order_date))
            
        conn.executemany(
            "INSERT INTO orders (customer, product, amount, created_at) VALUES (?, ?, ?, ?)",
            orders
        )
        conn.commit()


# Initialize DB and Seed Data on startup
init_db()
seed_db()


# ==========================================
# SQL Aggregations & Data Preparation
# ==========================================

def get_report_data():
    with get_db() as conn:
        # 1. Total number of orders
        total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

        # 2. Total revenue
        total_revenue = conn.execute("SELECT SUM(amount) FROM orders").fetchone()[0] or 0.0

        # 3. Top 5 products by revenue
        top_products = conn.execute("""
            SELECT product, SUM(amount) as revenue, COUNT(*) as count
            FROM orders
            GROUP BY product
            ORDER BY revenue DESC
            LIMIT 5
        """).fetchall()

        # 4. Orders per day for the last 7 days
        orders_per_day = conn.execute("""
            SELECT created_at, COUNT(*) as order_count, SUM(amount) as daily_revenue
            FROM orders
            WHERE created_at >= date('now', '-6 days')
            GROUP BY created_at
            ORDER BY created_at DESC
        """).fetchall()

        # 5. All orders for the comprehensive list table
        all_orders = conn.execute("""
            SELECT id, customer, product, amount, created_at
            FROM orders
            ORDER BY created_at DESC, id DESC
        """).fetchall()

    return {
        "today_date": datetime.date.today().isoformat(),
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "top_products": [dict(r) for r in top_products],
        "orders_per_day": [dict(r) for r in orders_per_day],
        "all_orders": [dict(r) for r in all_orders]
    }


# ==========================================
# HTML Template & PDF Generation Logic
# ==========================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @page {
            size: A4;
            margin: 20mm;
        }
        body {
            font-family: Arial, sans-serif;
            color: #333;
            line-height: 1.4;
        }
        h1 { color: #1a365d; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }
        h2 { color: #2b6cb0; margin-top: 25px; }
        
        .metrics-grid {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }
        .metric-card {
            background: #f7fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 15px;
            flex: 1;
        }
        .metric-title { font-size: 12px; color: #718096; text-transform: uppercase; }
        .metric-value { font-size: 24px; font-weight: bold; color: #2d3748; }

        /* Multi-page Table Rules */
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            border: 1px solid #e2e8f0;
            padding: 8px 12px;
            text-align: left;
            font-size: 12px;
        }
        th {
            background-color: #ebf8ff;
            color: #2c5282;
            font-weight: bold;
        }
        tr:nth-child(even) { background-color: #f7fafc; }

        /* Prevents row breaking across pages and repeats headers */
        thead { display: table-header-group; }
        tr { page-break-inside: avoid; }
    </style>
</head>
<body>
    <h1>Executive Sales Report</h1>
    <p><strong>Generated Date:</strong> {{ today_date }}</p>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-title">Total Orders</div>
            <div class="metric-value">{{ total_orders }}</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Total Revenue</div>
            <div class="metric-value">${{ "%.2f"|format(total_revenue) }}</div>
        </div>
    </div>

    <h2>Top 5 Products by Revenue</h2>
    <table>
        <thead>
            <tr>
                <th>Product</th>
                <th>Units Sold</th>
                <th>Total Revenue</th>
            </tr>
        </thead>
        <tbody>
            {% for prod in top_products %}
            <tr>
                <td>{{ prod.product }}</td>
                <td>{{ prod.count }}</td>
                <td>${{ "%.2f"|format(prod.revenue) }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <h2>Full Order Log</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Customer</th>
                <th>Product</th>
                <th>Amount</th>
                <th>Date</th>
            </tr>
        </thead>
        <tbody>
            {% for order in all_orders %}
            <tr>
                <td>#{{ order.id }}</td>
                <td>{{ order.customer }}</td>
                <td>{{ order.product }}</td>
                <td>${{ "%.2f"|format(order.amount) }}</td>
                <td>{{ order.created_at }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

def generate_pdf(data: dict, output_path: str):
    template = Template(HTML_TEMPLATE)
    rendered_html = template.render(**data)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(rendered_html, wait_until="networkidle")
        page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"}
        )
        browser.close()

# ==========================================
# FastAPI Endpoints
# ==========================================

@app.post("/reports", status_code=status.HTTP_201_CREATED)
def create_report(response: Response, force: bool = False):
    today = datetime.date.today().isoformat()
    
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM generated_reports WHERE report_date = ?", (today,)
        ).fetchone()

        # Idempotency check: Return existing report if force=False
        if existing and not force:
            response.status_code = status.HTTP_200_OK
            return {
                "message": "Report for today already exists.",
                "report_id": existing["id"],
                "download_url": f"/reports/{existing['id']}/download"
            }

        # Gather data and generate PDF
        data = get_report_data()
        filename = f"report_{today}_{int(datetime.datetime.now().timestamp())}.pdf"
        file_path = os.path.join(REPORTS_DIR, filename)
        
        generate_pdf(data, file_path)

        if existing and force:
            # Overwrite database entry if forced
            conn.execute(
                "UPDATE generated_reports SET file_path=?, total_orders=?, total_revenue=? WHERE id=?",
                (file_path, data["total_orders"], data["total_revenue"], existing["id"])
            )
            report_id = existing["id"]
        else:
            # Create new database record
            cursor = conn.execute(
                "INSERT INTO generated_reports (report_date, file_path, total_orders, total_revenue) VALUES (?, ?, ?, ?)",
                (today, file_path, data["total_orders"], data["total_revenue"])
            )
            report_id = cursor.lastrowid
        
        conn.commit()

    return {
        "message": "Report generated successfully.",
        "report_id": report_id,
        "download_url": f"/reports/{report_id}/download"
    }


@app.get("/reports/{report_id}")
def get_report_metadata(report_id: int):
    with get_db() as conn:
        report = conn.execute("SELECT * FROM generated_reports WHERE id = ?", (report_id,)).fetchone()
        
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    return {
        "id": report["id"],
        "report_date": report["report_date"],
        "total_orders": report["total_orders"],
        "total_revenue": report["total_revenue"],
        "created_at": report["created_at"],
        "download_url": f"/reports/{report['id']}/download"
    }


@app.get("/reports/{report_id}/download")
def download_report(report_id: int):
    with get_db() as conn:
        report = conn.execute("SELECT file_path FROM generated_reports WHERE id = ?", (report_id,)).fetchone()
        
    if not report or not os.path.exists(report["file_path"]):
        raise HTTPException(status_code=404, detail="PDF file not found")
        
    return FileResponse(
        path=report["file_path"],
        filename=f"sales_report_{report_id}.pdf",
        media_type="application/pdf"
    )