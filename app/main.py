from html import escape
from urllib.parse import parse_qs
import secrets
import sqlite3

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .db import connect, init_db, now, verify_password

app = FastAPI(title="Employee Support Tickets")
CATEGORIES = ("Hardware", "Software", "Network", "Access", "Other")
PRIORITIES = ("Low", "Medium", "High")
STATUSES = ("Open", "In Progress", "Resolved", "Closed")


@app.on_event("startup")
def startup() -> None:
    init_db()


def page(content: str, title: str = "Employee Support Tickets", error: str = "", status_code: int = 200) -> HTMLResponse:
    message = f'<p class="error" role="alert">{escape(error)}</p>' if error else ""
    return HTMLResponse(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(title)}</title>
<style>body{{font:16px Arial,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#222}}label{{display:block;margin-top:1rem}}input,textarea,select{{display:block;box-sizing:border-box;width:100%;max-width:620px;padding:.55rem;margin-top:.3rem}}button{{margin-top:1rem;padding:.55rem .9rem}}table{{border-collapse:collapse;width:100%;margin:1rem 0}}td,th{{border:1px solid #bbb;padding:.5rem;text-align:left}}.error{{color:#8b0000}}.comment{{border-bottom:1px solid #ccc;padding:.5rem 0}}nav{{margin-bottom:1rem}}</style></head>
<body><nav><a href="/tickets">Tickets</a> · <a href="/tickets/new">New ticket</a> · <form method="post" action="/logout" style="display:inline"><button>Log out</button></form></nav><main>{message}{content}</main></body></html>""", status_code=status_code)


def fields(request: Request) -> dict[str, str]:
    # Parse ordinary browser form bodies without requiring python-multipart.
    raw = request.scope.get("_form_data")
    if raw is None:
        return {}
    return {key: values[0] if values else "" for key, values in raw.items()}


async def form_fields(request: Request) -> dict[str, str]:
    raw = await request.body()
    parsed = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
    request.scope["_form_data"] = parsed
    return fields(request)


def current_user(request: Request):
    token = request.cookies.get("ticket_session", "")
    if not token:
        return None
    with connect() as db:
        return db.execute("SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?", (token,)).fetchone()


def ticket_for(user, ticket_id: int):
    with connect() as db:
        ticket = db.execute("""SELECT t.*,u.name AS creator FROM tickets t JOIN users u ON u.id=t.created_by WHERE t.id=?""", (ticket_id,)).fetchone()
    if ticket is None or (user["role"] == "employee" and ticket["created_by"] != user["id"]):
        return None
    return ticket


def login_required(request: Request):
    return current_user(request)


def options(values, selected):
    return "".join(f'<option value="{escape(v)}"{" selected" if v == selected else ""}>{escape(v)}</option>' for v in values)


def ticket_form(ticket=None, error=""):
    ticket = dict(ticket or {"title": "", "description": "", "category": "Hardware", "priority": "Medium"})
    content = f'''<h1>{"Edit ticket" if ticket.get("id") else "New ticket"}</h1>
<form method="post"><label>Title <input name="title" maxlength="100" required value="{escape(ticket["title"])}"></label>
<label>Description <textarea name="description" required rows="5">{escape(ticket["description"])}</textarea></label>
<label>Category <select name="category">{options(CATEGORIES, ticket["category"])}</select></label>
<label>Priority <select name="priority">{options(PRIORITIES, ticket["priority"])}</select></label>
<button type="submit">Save</button></form>'''
    return page(content, "Ticket", error)


@app.get("/", response_class=HTMLResponse)
def home():
    return page('''<h1>Employee Support Tickets</h1><p>Sign in with a demo account.</p>
<form method="post" action="/login"><label>Username <input name="username" required></label>
<label>Password <input type="password" name="password" required></label><button>Sign in</button></form>''')


@app.post("/login")
async def login(request: Request):
    data = await form_fields(request)
    with connect() as db:
        user = db.execute("SELECT * FROM users WHERE username=?", (data.get("username", ""),)).fetchone()
        if not user or not verify_password(data.get("password", ""), user["password_hash"]):
            return page('<h1>Sign in</h1><form method="post" action="/login"><label>Username <input name="username" required></label><label>Password <input type="password" name="password" required></label><button>Sign in</button></form>', error="Username or password is incorrect.")
        token = secrets.token_urlsafe(32)
        db.execute("INSERT INTO sessions(token,user_id,created_at) VALUES(?,?,?)", (token, user["id"], now()))
    response = RedirectResponse("/tickets", status_code=303)
    response.set_cookie("ticket_session", token, httponly=True, samesite="lax")
    return response


@app.post("/logout")
def logout(request: Request):
    token = request.cookies.get("ticket_session", "")
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE token=?", (token,))
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("ticket_session")
    return response


@app.get("/tickets", response_class=HTMLResponse)
def tickets(request: Request):
    user = login_required(request)
    if not user:
        return RedirectResponse("/", status_code=303)
    with connect() as db:
        if user["role"] == "support":
            rows = db.execute("SELECT t.*,u.name AS creator FROM tickets t JOIN users u ON u.id=t.created_by ORDER BY t.id").fetchall()
        else:
            rows = db.execute("SELECT t.*,u.name AS creator FROM tickets t JOIN users u ON u.id=t.created_by WHERE t.created_by=? ORDER BY t.id", (user["id"],)).fetchall()
    table = "".join(f'<tr><td><a href="/tickets/{r["id"]}">#{r["id"]} {escape(r["title"])}</a></td><td>{escape(r["creator"])}</td><td>{escape(r["category"])}</td><td>{escape(r["priority"])}</td><td>{escape(r["status"])}</td></tr>' for r in rows)
    return page(f'<h1>Tickets</h1><table><thead><tr><th>Ticket</th><th>Created by</th><th>Category</th><th>Priority</th><th>Status</th></tr></thead><tbody>{table}</tbody></table>')


@app.get("/tickets/new", response_class=HTMLResponse)
def new_ticket_page(request: Request):
    if not login_required(request):
        return RedirectResponse("/", status_code=303)
    return ticket_form()


@app.post("/tickets/new")
async def create_ticket(request: Request):
    user = login_required(request)
    if not user:
        return RedirectResponse("/", status_code=303)
    data = await form_fields(request)
    title, description = data.get("title", "").strip(), data.get("description", "").strip()
    category, priority = data.get("category", ""), data.get("priority", "")
    if not title or not description or len(title) > 100 or category not in CATEGORIES or priority not in PRIORITIES:
        return ticket_form({"title": title, "description": description, "category": category if category in CATEGORIES else "Hardware", "priority": priority if priority in PRIORITIES else "Medium"}, "Title and description are required; title must be 100 characters or fewer and category and priority must be valid.")
    stamp = now()
    with connect() as db:
        cur = db.execute("INSERT INTO tickets(title,description,category,priority,status,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (title, description, category, priority, "Open", user["id"], stamp, stamp))
        ticket_id = cur.lastrowid
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_detail(request: Request, ticket_id: int):
    user = login_required(request)
    if not user:
        return RedirectResponse("/", status_code=303)
    ticket = ticket_for(user, ticket_id)
    if not ticket:
        return page("<h1>Ticket not found</h1>", error="Ticket not found.", status_code=404)
    with connect() as db:
        comments = db.execute("SELECT c.*,u.name FROM comments c JOIN users u ON u.id=c.user_id WHERE c.ticket_id=? ORDER BY c.id", (ticket_id,)).fetchall()
    lines = "".join(f'<div class="comment"><b>{escape(c["name"])}</b> · {escape(c["created_at"])}<p>{escape(c["body"])}</p></div>' for c in comments)
    controls = f'<p><a href="/tickets/{ticket_id}/edit">Edit ticket</a></p>' if user["role"] == "employee" and ticket["status"] != "Closed" else ""
    if user["role"] == "support":
        controls += f'<form method="post" action="/tickets/{ticket_id}/status"><label>Status <select name="status">{options(STATUSES, ticket["status"])}</select></label><button>Update status</button></form>'
    content = f'''<h1>#{ticket["id"]} {escape(ticket["title"])}</h1><p>{escape(ticket["description"])}</p>
<p>Category: {escape(ticket["category"])} · Priority: {escape(ticket["priority"])} · Status: {escape(ticket["status"])}</p>
<p>Created by {escape(ticket["creator"])} · Created {escape(ticket["created_at"])} · Updated {escape(ticket["updated_at"])}</p>{controls}
<h2>Comments</h2>{lines}<form method="post" action="/tickets/{ticket_id}/comments"><label>Comment (up to 500 characters)<textarea name="body" maxlength="500" required></textarea></label><button>Add comment</button></form>'''
    return page(content, f'Ticket #{ticket_id}')


@app.get("/tickets/{ticket_id}/edit", response_class=HTMLResponse)
def edit_ticket_page(request: Request, ticket_id: int):
    user = login_required(request)
    if not user:
        return RedirectResponse("/", status_code=303)
    ticket = ticket_for(user, ticket_id)
    if not ticket or user["role"] != "employee" or ticket["status"] == "Closed":
        return page("<h1>Ticket cannot be edited</h1>", error="Ticket cannot be edited.", status_code=403)
    return ticket_form(ticket)


@app.post("/tickets/{ticket_id}/edit")
async def edit_ticket(request: Request, ticket_id: int):
    user = login_required(request)
    if not user:
        return RedirectResponse("/", status_code=303)
    ticket = ticket_for(user, ticket_id)
    if not ticket or user["role"] != "employee" or ticket["status"] == "Closed":
        return page("<h1>Ticket cannot be edited</h1>", error="Ticket cannot be edited.", status_code=403)
    data = await form_fields(request)
    title, description = data.get("title", "").strip(), data.get("description", "").strip()
    category, priority = data.get("category", ""), data.get("priority", "")
    if not title or not description or len(title) > 100 or category not in CATEGORIES or priority not in PRIORITIES:
        return ticket_form({**dict(ticket), "title": title, "description": description, "category": category if category in CATEGORIES else ticket["category"], "priority": priority if priority in PRIORITIES else ticket["priority"]}, "Title and description are required; title must be 100 characters or fewer and category and priority must be valid.")
    with connect() as db:
        db.execute("UPDATE tickets SET title=?,description=?,category=?,priority=?,updated_at=? WHERE id=?", (title, description, category, priority, now(), ticket_id))
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.post("/tickets/{ticket_id}/status")
async def update_status(request: Request, ticket_id: int):
    user = login_required(request)
    if not user:
        return RedirectResponse("/", status_code=303)
    if user["role"] != "support":
        return page("<h1>Access denied</h1>", error="Only support staff can change a status.", status_code=403)
    ticket = ticket_for(user, ticket_id)
    data = await form_fields(request)
    if not ticket or data.get("status") not in STATUSES:
        return page("<h1>Could not update status</h1>", error="Ticket or status is invalid.", status_code=400)
    with connect() as db:
        db.execute("UPDATE tickets SET status=?,updated_at=? WHERE id=?", (data["status"], now(), ticket_id))
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.post("/tickets/{ticket_id}/comments")
async def add_comment(request: Request, ticket_id: int):
    user = login_required(request)
    if not user:
        return RedirectResponse("/", status_code=303)
    ticket = ticket_for(user, ticket_id)
    if not ticket:
        return page("<h1>Ticket not found</h1>", error="Ticket not found.", status_code=404)
    body = (await form_fields(request)).get("body", "").strip()
    if not body or len(body) > 500:
        return page(f'<h1>Comment not saved</h1><p><a href="/tickets/{ticket_id}">Back to ticket</a></p>', error="Comment is required and must be 500 characters or fewer.")
    stamp = now()
    with connect() as db:
        db.execute("INSERT INTO comments(ticket_id,user_id,body,created_at) VALUES(?,?,?,?)", (ticket_id, user["id"], body, stamp))
        db.execute("UPDATE tickets SET updated_at=? WHERE id=?", (stamp, ticket_id))
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)
