# PDF Report Generator

## Stage 4 note
Right now report generation happens synchronously inside the POST /reports request, which takes a few seconds. For a single user clicking one button, this is acceptable. I would move this work into a background job (like the Inngest pattern from A7) once report generation grows heavier — e.g., much larger datasets, more complex rendering, or many concurrent users — because a multi-second request blocks the client and doesn't scale well under load.


## Stage 5 note
The duplicate-request check (same day → same report) protects against a user double-clicking "Generate Report" and accidentally creating multiple identical files (and wasted work/storage) for the same day's data. A real-world example: an e-commerce site that emails an order confirmation on each "Generate Invoice" click — without this check, a customer who double-clicks could receive two duplicate confirmation emails, which looks unprofessional and can cause billing confusion.