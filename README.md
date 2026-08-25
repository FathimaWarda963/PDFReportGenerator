# PDF Report Generator

## Stage 4 note
Right now report generation happens synchronously inside the POST /reports request, which takes a few seconds. For a single user clicking one button, this is acceptable. I would move this work into a background job (like the Inngest pattern from A7) once report generation grows heavier — e.g., much larger datasets, more complex rendering, or many concurrent users — because a multi-second request blocks the client and doesn't scale well under load.