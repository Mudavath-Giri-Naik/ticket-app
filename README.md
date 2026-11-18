# Employee Support Tickets

A small local ticket app built with Python, FastAPI, SQLite, and simple HTML pages.

## What AI generated

Codex CLI generated the FastAPI pages and routes, SQLite tables and sample records, demo login, ticket creation and editing, role checks, status changes, comments, and pytest tests.

## What I changed

I approved the plan and supplied the GitHub repository URL. I did not make separate feature code edits. During review, I replaced FastAPI's deprecated startup hook with a lifespan handler.

## What I checked

- Started the app at `http://127.0.0.1:8000` and checked it in Chrome through Playwright.
- Passed 43 live browser and API checks for login, role access, ticket create/edit, statuses, comments, invalid input, field limits, and timestamp updates.
- Ran `python -m pytest -q`: 7 passed, 1 warning. The warning is from Starlette's `TestClient` use of `httpx`.
- Ran `python -m compileall -q app tests` successfully.
- Reviewed the app diff, input checks, error responses, secrets, and access rules.
- Saved real screenshots in `screenshots/` for the app pages, errors, comments, Git diff, and pytest output. The screenshots are local evidence and are ignored by Git.

## Known gaps

- No functional defect appeared in the 43 live checks and 7 pytest tests, so no defect was reproduced or fixed.
- Cursor, OpenCode, and Spec Kit were not used. The Day 3 spec was not in this folder.
- Demo passwords are made up, generated on first database initialization, and saved in `.demo_credentials.txt`, which is ignored by Git.
- No email alerts, file upload, real login system, ticket deletion, or reports.
- This training app has not had a production security review.
