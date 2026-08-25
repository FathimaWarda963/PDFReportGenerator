# PDF Report Generator

A small backend service that queries a SQLite database, renders the results into a PDF report using a headless browser, and serves the file by link.

**Dataset chosen:** Option A — the little shop (seeded orders data).

## How to run

1. **Clone the repo and enter the folder:**
   \`\`\`bash
   git clone https://github.com/FathimaWarda963/PDFReportGenerator.git
   cd PDFReportGenerator
   \`\`\`

2. **Create a virtual environment and install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   playwright install chromium

3. **Seed the database:**
   ```bash
   python seed.py

4. **Run the API:**
   ```bash
    uvicorn main:app --reload --port 8000

5. **Generate a report:**
   ```bash
   curl -i -X POST http://localhost:8000/reports


6. **Download it (replace `<id>` with the id from step 5):**
   ```bash
   curl -o my-report.pdf http://localhost:8000/reports/<id>/file


## Aggregation SQL

Total orders and total revenue:
```sql
SELECT COUNT(*) AS count FROM orders;
SELECT SUM(amount) AS total FROM orders;
```

Top 5 products by revenue:
```sql
SELECT product, SUM(amount) AS revenue
FROM orders
GROUP BY product
ORDER BY revenue DESC
LIMIT 5;
```

Orders per day for the last 7 days:
```sql
SELECT created_at AS day, COUNT(*) AS count
FROM orders
WHERE created_at >= ?
GROUP BY created_at
ORDER BY created_at ASC;
```

## Download proof

```bash
$ curl -i -X POST http://localhost:8000/reports
HTTP/1.1 201 Created
{"id":"cc78c670-a2c3-4001-b9be-d7d73fe93a17","file":"/reports/cc78c670-a2c3-4001-b9be-d7d73fe93a17/file"}

$ curl -o my-report.pdf http://localhost:8000/reports/cc78c670-a2c3-4001-b9be-d7d73fe93a17/file
  % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                 Dload  Upload  Total   Spent   Left   Speed
100  66118 100  66118   0      0 264.7k      0                              0
```

## Stage 4 note
Right now report generation happens synchronously inside the POST /reports request, which takes a few seconds. For a single user clicking one button, this is acceptable. I would move this work into a background job (like the Inngest pattern from A7) once report generation grows heavier — e.g., much larger datasets, more complex rendering, or many concurrent users — because a multi-second request blocks the client and doesn't scale well under load.

## Stage 5 note
The duplicate-request check (same day → same report) protects against a user double-clicking "Generate Report" and accidentally creating multiple identical files (and wasted work/storage) for the same day's data. A real-world example: an e-commerce site that emails an order confirmation on each "Generate Invoice" click — without this check, a customer who double-clicks could receive two duplicate confirmation emails, which looks unprofessional and can cause billing confusion.

## PDF sample (page 1)

![Report sample](ReportScreenshot.png)


## Big-table experiment
Seeding 5,000 orders instead of 200 and generating a report took approximately 1.94 seconds, compared to roughly half that with 200 rows (based on Stage 4 testing) — response time scales with the size of the HTML table the headless browser has to render (126 pages at 5,000 rows vs. 6 pages at 200 rows). This makes it clear that doing this work synchronously inside a request does not scale indefinitely: with much larger datasets (tens of thousands of rows) or many concurrent users generating reports at once, the request would take long enough to risk timeouts and would block server resources that could be serving other requests. This is exactly the case for moving generation into a background job, as A7 does.

## AI vs me

### My prompt (written from memory, without copying this assignment's wording)

The basic idea of this assignment is to create a PDF report generator. The chain is that the data required would be stored in a database, like SQLite, and then the code would include SQL functions that would group them and "prepare" them beforehand for uploading to PDF format.

Build this in Python, using FastAPI as the web framework and Playwright for rendering the PDF.

Specifically: create a SQLite database called report.db with one table orders (columns: id, customer text, product text, amount number, created_at date). Write a seed script that inserts ~200 random orders (5-6 product names, random amounts between 5 and 200, random dates in the last 30 days) — and make sure running the seed script twice doesn't double the data (clear the table first).

Then write SQL aggregation functions that produce four things: total number of orders, total revenue (sum of amount), the top 5 products by revenue (grouped and ordered), and orders per day for the last 7 days (grouped by date).

After this, the code must include an HTML section that would define the structure of the output PDF, along with including the features from the already written SQL functions — a title with today's date, the two totals, a small table for the top 5 products, and a long table listing every order. Render this HTML into an actual PDF file using a headless browser (like Playwright), not just print-to-PDF styling alone. Since the long orders table will span multiple pages, make sure table rows never get cut in half across a page break, and make sure the table header repeats on every page.

It also needs to have different functions such as if the same report is asked to be generated twice on the same day, it shouldn't be merely duplicated, but rather created only once per day — return the existing report's id with a 200 status if one already exists for today, and only create a new one (with a 201 status) if none exists yet or if the caller explicitly asks for a fresh one (e.g. a force flag).

Additionally, there needs to be certain API endpoints that would basically deliver the final piece to the users: a POST endpoint that runs the whole pipeline and returns the report's id and a link to download it, a GET endpoint that returns a report's metadata by id (404 if it doesn't exist), and a separate GET endpoint that actually serves the PDF file itself so it can be downloaded — the file should live on disk and be served by that link, not embedded as bytes inside any JSON response.

### What the AI did better — and did I understand it?

- **Jinja2 templates instead of raw f-strings** for the HTML. This is cleaner and more standard than my string-concatenation approach, and safer against malformed HTML if a field ever contained special characters.
- **Added a units-sold column** to the top-products table (COUNT alongside SUM), which I didn't ask for but is a genuinely useful addition for a sales report.
- **Nicer visual design** — metric cards, color palette, and consistent margins that my version lacks.
- **A UNIQUE constraint on report_date** in its reports table, so the "one report per day" rule is partly enforced by the database schema itself, not just application code.

I understand all of these choices and could explain why each one works.

### What did it get wrong or silently ignore?

- **It initially crashed on every request.** It used Playwright's async API (`async_playwright`) inside async route handlers, which triggers a known Windows-specific asyncio bug (`NotImplementedError` in subprocess creation). I diagnosed this and fixed it by switching to Playwright's sync API — the same choice I'd already made in my own version, for a different reason (matching my sync FastAPI routes).
- **Its `force=true` behavior mutates history.** Instead of creating a new report id (like mine does), it UPDATEs the existing row and overwrites the file on disk. That means a previously shared download link (`/reports/1/download`) can silently start serving completely different content later, and the old PDF file becomes orphaned on disk with no database record pointing to it. This breaks the "artifact" principle from the assignment — a stored file's link should always point to the same content.
- **No standalone seed script.** It seeds the database automatically on every server startup instead of via a separate, explicitly-run script, which the assignment's Stage 1 specifically asked for.
- **Sequential integer ids** instead of UUIDs, which makes it trivial for a client to guess/enumerate other reports' ids.

### What did my prompt forget to specify — and what did the AI silently decide for you?

- I never said "use the synchronous Playwright API" — the AI defaulted to async and it broke on Windows. My own version's simplicity (sync routes, sync Playwright) avoided this problem by accident, not because I explicitly ruled it out in the prompt.
- I never specified whether a forced regeneration should create a brand-new report record or overwrite the existing one — the AI chose to overwrite, which has real consequences for link stability that I didn't think to prevent in advance.
- I never explicitly said "the seed script should be runnable on its own, separately from the server" — the AI folded seeding into server startup instead.
- I never specified id format (UUID vs auto-increment integer) — the AI defaulted to sequential integers.

### One rematch

I would revise my prompt to add: "Use Playwright's synchronous API, not the async API. Provide the seed logic as a separate, standalone script rather than running it automatically on server startup. On a forced regeneration, always create a new report record with a new id rather than overwriting the existing one, so that any previously shared download link keeps working and always serves the same file." This directly targets the three biggest gaps this rematch revealed.