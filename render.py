import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from report_data import get_report_data, get_connection


def build_html(data):
    today = datetime.now().strftime("%Y-%m-%d")

    top_products_rows = "".join(
        f"<tr><td>{p['product']}</td><td>${p['revenue']:.2f}</td></tr>"
        for p in data["top_products"]
    )
    orders_per_day_rows = "".join(
        f"<tr><td>{d['day']}</td><td>{d['count']}</td></tr>"
        for d in data["orders_per_day"]
    )
    # Pull every order for the long table
    conn = get_connection()
    all_orders = conn.execute(
        "SELECT customer, product, amount, created_at FROM orders ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    all_orders_rows = "".join(
        f"<tr><td>{o['customer']}</td><td>{o['product']}</td>"
        f"<td>${o['amount']:.2f}</td><td>{o['created_at']}</td></tr>"
        for o in all_orders
    )

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                color: #222;
                margin: 40px;
            }}
            h1 {{
                border-bottom: 2px solid #333;
                padding-bottom: 8px;
            }}
            .totals {{
                display: flex;
                gap: 40px;
                margin: 20px 0;
            }}
            .totals div {{
                background: #f4f4f4;
                padding: 12px 20px;
                border-radius: 6px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            thead {{
                display: table-header-group;
            }}
            tr {{
                break-inside: avoid;
            }}
            th, td {{
                border: 1px solid #ccc;
                padding: 6px 10px;
                text-align: left;
                font-size: 12px;
            }}
            th {{
                background: #333;
                color: white;
            }}
            h2 {{
                margin-top: 40px;
            }}
        </style>
    </head>
    <body>
        <h1>Sales Report — {today}</h1>

        <div class="totals">
            <div><strong>Total Orders:</strong> {data['total_orders']}</div>
            <div><strong>Total Revenue:</strong> ${data['total_revenue']:.2f}</div>
        </div>

        <h2>Top 5 Products by Revenue</h2>
        <table>
            <thead><tr><th>Product</th><th>Revenue</th></tr></thead>
            <tbody>{top_products_rows}</tbody>
        </table>

        <h2>Orders per Day (last {data.get('days_window', 7)} days)</h2>
        <table>
            <thead><tr><th>Date</th><th>Order Count</th></tr></thead>
            <tbody>{orders_per_day_rows}</tbody>
        </table>
        
        <h2>All Orders ({len(all_orders)})</h2>
        <table>
            <thead><tr><th>Customer</th><th>Product</th><th>Amount</th><th>Date</th></tr></thead>
            <tbody>{all_orders_rows}</tbody>
        </table>
    </body>
    </html>
    """
    return html


def render_pdf(html, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.pdf(path=output_path, format="A4", print_background=True)
        browser.close()


if __name__ == "__main__":
    data = get_report_data()
    html = build_html(data)
    render_pdf(html, "reports/test.pdf")
    print("Saved reports/test.pdf")