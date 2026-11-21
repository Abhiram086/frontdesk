import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse, urlunparse

import bcrypt
import psycopg
import pytest
from fastapi.testclient import TestClient

# Point tests at a dedicated test database before importing app.db
BASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:pw@localhost:5432/frontdesk"
)
parsed = urlparse(BASE_URL)
TEST_DB_NAME = "frontdesk_test"
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", urlunparse(parsed._replace(path=f"/{TEST_DB_NAME}"))
)
ADMIN_URL = urlunparse(parsed._replace(path="/postgres"))

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ.setdefault("JWT_SECRET", "test-secret-key")

MIGRATION_SQL = (
    Path(__file__).resolve().parent.parent / "migrations" / "001_init.sql"
).read_text(encoding="utf-8")


def _reset_test_db():
    # Create frontdesk_test once if it does not exist yet
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,)
        ).fetchone()
        if not exists:
            conn.execute(f"CREATE DATABASE {TEST_DB_NAME}")

    # Wipe and rebuild schema cleanly for the test session
    with psycopg.connect(TEST_DB_URL, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.execute(MIGRATION_SQL)

        pw = bcrypt.hashpw(b"Frontdesk@123", bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            ("Meera", "meera@arvo.test", pw, "manager"),
        )
        for i in range(1, 4):
            conn.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                (f"Agent {i}", f"agent{i}@arvo.test", pw, "agent"),
            )
        conn.execute(
            "INSERT INTO holidays (day, name) VALUES ('2026-12-25', 'Christmas')"
        )


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    _reset_test_db()


@pytest.fixture(scope="session")
def client(setup_db):
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    # autocommit=True keeps the connection usable after expected trigger errors
    with psycopg.connect(TEST_DB_URL, autocommit=True) as conn:
        yield conn


def _login(client: TestClient, email: str) -> str:
    res = client.post(
        "/api/auth/login", json={"email": email, "password": "Frontdesk@123"}
    )
    assert res.status_code == 200
    return res.json()["token"]


@pytest.fixture(scope="session")
def manager_token(client):
    return _login(client, "meera@arvo.test")


@pytest.fixture(scope="session")
def agent_tokens(client):
    return [_login(client, f"agent{i}@arvo.test") for i in (1, 2, 3)]


@pytest.fixture(scope="session")
def agent_token(agent_tokens):
    return agent_tokens[0]


@pytest.fixture
def new_ticket(client):
    res = client.post(
        "/api/public/tickets",
        json={
            "name": "Ravi",
            "email": "ravi@client.test",
            "subject": "Cannot export invoices",
            "body": "Export button throws 500 error.",
            "priority": "medium",
        },
    )
    assert res.status_code == 200
    token = res.json()["token"]

    with psycopg.connect(TEST_DB_URL) as conn:
        tid = conn.execute(
            "SELECT id FROM tickets WHERE public_token = %s", (token,)
        ).fetchone()[0]
    return SimpleNamespace(id=tid, token=token)


@pytest.fixture
def claimed_ticket(client, agent_token, new_ticket):
    res = client.post(
        f"/api/tickets/{new_ticket.id}/claim",
        headers={"Authorization": f"Bearer {agent_token}"},
    )
    assert res.status_code == 200
    return new_ticket