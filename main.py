import sqlite3
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from report_data import get_report_data, get_connection as get_orders_connection
from render import build_html, render_pdf

app = FastAPI()

DB_PATH = "report.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_reports_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


create_reports_table()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reports", status_code=201)
def create_report(force: bool = False):
    today = datetime.now().strftime("%Y-%m-%d")

    if not force:
        conn = get_connection()
        existing = conn.execute(
            "SELECT * FROM reports WHERE created_at LIKE ? ORDER BY created_at DESC LIMIT 1",
            (f"{today}%",)
        ).fetchone()
        conn.close()

        if existing is not None:
            return JSONResponse(
                status_code=200,
                content={
                    "id": existing["id"],
                    "file": f"/reports/{existing['id']}/file"
                }
            )

    report_id = str(uuid.uuid4())
    output_path = f"reports/{report_id}.pdf"

    data = get_report_data()
    html = build_html(data)
    render_pdf(html, output_path)

    created_at = datetime.now().isoformat()

    conn = get_connection()
    conn.execute(
        "INSERT INTO reports (id, path, created_at) VALUES (?, ?, ?)",
        (report_id, output_path, created_at)
    )
    conn.commit()
    conn.close()

    return {
        "id": report_id,
        "file": f"/reports/{report_id}/file"
    }


@app.get("/reports/{report_id}")
def get_report(report_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM reports WHERE id = ?", (report_id,)
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": row["id"],
        "path": row["path"],
        "created_at": row["created_at"],
        "file": f"/reports/{row['id']}/file"
    }


@app.get("/reports/{report_id}/file")
def get_report_file(report_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM reports WHERE id = ?", (report_id,)
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(row["path"], media_type="application/pdf", filename=f"{report_id}.pdf")