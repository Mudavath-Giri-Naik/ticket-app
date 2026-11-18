import secrets
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import db
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tickets.db")
    with TestClient(app) as test_client:
        yield test_client


def sign_in(client, username):
    # Use a fresh made-up password for each test login.
    password = secrets.token_urlsafe(16)
    with db.connect() as conn:
        user = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if user:
            conn.execute("UPDATE users SET password_hash=? WHERE id=?", (db.hash_password(password), user["id"]))
    response = client.post("/login", data={"username": username, "password": password}, follow_redirects=False)
    assert response.status_code == 303
    return response


def test_bad_password_rejected(client):
    response = client.post("/login", data={"username": "ravi", "password": secrets.token_urlsafe(16)})
    assert response.status_code == 200
    assert "incorrect" in response.text


def test_empty_title_and_description_rejected(client):
    sign_in(client, "ravi")
    for data in ({"title": "", "description": "body", "category": "Hardware", "priority": "Low"},
                 {"title": "Title", "description": " ", "category": "Hardware", "priority": "Low"}):
        response = client.post("/tickets/new", data=data)
        assert "required" in response.text
    with db.connect() as conn:
        assert conn.execute("SELECT count(*) FROM tickets").fetchone()[0] == 5


def test_title_over_100_rejected(client):
    sign_in(client, "ravi")
    response = client.post("/tickets/new", data={"title": "x" * 101, "description": "body", "category": "Hardware", "priority": "Low"})
    assert "100 characters" in response.text


def test_employee_cannot_change_status(client):
    sign_in(client, "ravi")
    response = client.post("/tickets/1/status", data={"status": "Closed"})
    assert response.status_code == 403
    assert "Only support staff" in response.text
    with db.connect() as conn:
        assert conn.execute("SELECT status FROM tickets WHERE id=1").fetchone()[0] == "Open"


def test_employee_sees_only_own_tickets(client):
    sign_in(client, "ravi")
    response = client.get("/tickets")
    assert "Laptop not charging" in response.text
    assert "Cannot log in to VPN" not in response.text
    assert client.get("/tickets/2").status_code == 404


def test_support_sees_all_tickets(client):
    sign_in(client, "karan")
    response = client.get("/tickets")
    assert response.status_code == 200
    for title in ("Laptop not charging", "Cannot log in to VPN", "Request a second monitor"):
        assert title in response.text


def test_closed_ticket_cannot_be_edited_but_accepts_comment(client):
    sign_in(client, "anita")
    assert client.get("/tickets/5/edit").status_code == 403
    assert client.post("/tickets/5/edit", data={"title": "Changed", "description": "Changed", "category": "Hardware", "priority": "Low"}).status_code == 403
    response = client.post("/tickets/5/comments", data={"body": "Made-up follow-up"}, follow_redirects=False)
    assert response.status_code == 303
    with db.connect() as conn:
        assert conn.execute("SELECT body FROM comments WHERE ticket_id=5").fetchone()[0] == "Made-up follow-up"
