# Employee Support Tickets

A small local ticket app built with Python, FastAPI, SQLite, and HTML pages.

## What AI generated

Codex CLI generated the FastAPI pages and routes, SQLite tables and sample records, demo login, ticket creation and editing, role checks, status changes, comments, and pytest tests.

## What I changed

I approved the plan and supplied the GitHub repository URL. I did not make separate code edits.

## What I checked

I initialized the SQLite database and confirmed the three sample users and five specified tickets and statuses. Python's `compileall` check passed for the app files. I reviewed the source for input checks, credentials, error responses, and access checks.

The FastAPI app could not be started and pytest could not run in this environment: FastAPI and pytest were not installed, and pip could not reach its package index. The tests are in `tests/test_app.py` and need to be run after installing `requirements.txt`.

## Known gaps

- Runtime feature checks, role checks, and bad input checks were not run.
- Pytest was not run.
- No browser screenshots were captured.
- Demo passwords are generated locally on first database initialization and saved in `.demo_credentials.txt`, which is ignored by Git. They are made-up and for local use only.
- No email alerts, file upload, production login, ticket deletion, or reports.
- This is a training app and has not had a production security review.
