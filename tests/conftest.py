"""Test fixtures.

Tests run against SQLite in memory, not Postgres: no external service needed,
so `pytest` works on a laptop and in CI with no setup. The application code is
plain SQLAlchemy, so the same statements run on both.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        # One shared in-memory database for the whole test, instead of a new
        # empty one per connection.
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """A registered, logged-in user's Authorization header."""
    creds = {"email": "test@example.com", "password": "password123"}
    client.post("/auth/signup", json=creds)
    r = client.post("/auth/login",
                    data={"username": creds["email"], "password": creds["password"]})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
