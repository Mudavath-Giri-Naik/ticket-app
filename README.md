# Employee Support Tickets

A small local ticket app built with Python, FastAPI, SQLite, and simple HTML pages.

## What AI generated

Codex CLI generated the FastAPI pages and routes, SQLite tables and sample records, demo login, ticket creation and editing, role checks, status changes, comments, and pytest tests.

## What I changed

I approved the plan and supplied the GitHub repository URL. During review, I replaced FastAPI's deprecated startup hook with a lifespan handler and changed the test helper to generate a fresh made-up password for each test login.

## What I checked

- Started the app at `http://127.0.0.1:8000` and checked it in Chrome through Playwright.
- Passed 43 live browser and API checks for login, role access, ticket create/edit, statuses, comments, invalid input, field limits, and timestamp updates.
- Ran `python -m pytest -q`: 7 passed, 1 warning. The warning is from Starlette's `TestClient` use of `httpx`.
- Ran `python -m compileall -q app tests` successfully.
- Reviewed the app diff, input checks, error responses, secrets, and access rules.
- Saved real screenshots in `screenshots/` for the app pages, errors, comments, Git diffs, defect before/after, and pytest output. Screenshots are local evidence and ignored by Git.

## Known gaps

- A made-up test password was present in the initial app commit. The current test helper generates passwords at runtime; no real credentials were used. The old fake value remains in Git history.
- No user-facing ticket defect appeared in the live checks. The test password code issue was fixed and retested.
- Cursor, OpenCode, and Spec Kit were not used. The Day 3 spec was not in this folder.
- Demo passwords are made up, generated on first database initialization, and saved in `.demo_credentials.txt`, which is ignored by Git.
- No email alerts, file upload, real login system, ticket deletion, or reports.
- This training app has not had a production security review.
