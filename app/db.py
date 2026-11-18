import hashlib
import secrets
import sqlite3
from contextlib import contextmanager
from typing import Iterator
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tickets.db"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    actual = hash_password(password, salt).split("$", 1)[1]
    return secrets.compare_digest(actual, expected)


def init_db() -> None:
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, username TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('employee', 'support')), password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 100),
            description TEXT NOT NULL CHECK(length(trim(description)) > 0),
            category TEXT NOT NULL CHECK(category IN ('Hardware','Software','Network','Access','Other')),
            priority TEXT NOT NULL CHECK(priority IN ('Low','Medium','High')),
            status TEXT NOT NULL CHECK(status IN ('Open','In Progress','Resolved','Closed')),
            created_by INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL REFERENCES tickets(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL CHECK(length(trim(body)) BETWEEN 1 AND 500), created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL
        );
        """)
        if db.execute("SELECT count(*) FROM users").fetchone()[0] == 0:
            people = [("Ravi", "ravi", "employee"), ("Anita", "anita", "employee"), ("Karan", "karan", "support")]
            passwords = {username: secrets.token_urlsafe(10) for _, username, _ in people}
            db.executemany("INSERT INTO users(name,username,role,password_hash) VALUES(?,?,?,?)",
                [(name, username, role, hash_password(passwords[username])) for name, username, role in people])
            (DB_PATH.parent / ".demo_credentials.txt").write_text(
                "Made-up demo credentials. Do not reuse these passwords.\n" + "\n".join(
                    f"{username}: {passwords[username]}" for _, username, _ in people
                ) + "\n", encoding="utf-8")
        if db.execute("SELECT count(*) FROM tickets").fetchone()[0] == 0:
            ids = {r["username"]: r["id"] for r in db.execute("SELECT id,username FROM users")}
            examples = [
                ("Laptop not charging", "Laptop does not charge when plugged in.", "Hardware", "High", "Open", "ravi"),
                ("Cannot log in to VPN", "VPN login fails.", "Network", "High", "In Progress", "anita"),
                ("Need access to the shared project folder", "Please grant access to the shared project folder.", "Access", "Medium", "Open", "ravi"),
                ("Excel keeps crashing on startup", "Excel closes when I start it.", "Software", "Medium", "Resolved", "anita"),
                ("Request a second monitor", "Please provide a second monitor.", "Hardware", "Low", "Closed", "anita"),
            ]
            stamp = now()
            db.executemany("INSERT INTO tickets(title,description,category,priority,status,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                [(title, description, category, priority, status, ids[username], stamp, stamp)
                 for title, description, category, priority, status, username in examples])
