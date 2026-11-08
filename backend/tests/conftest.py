import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp}/test.db")
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["PBKDF2_ITERATIONS"] = "1000"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app, init_db


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    init_db()
    with TestClient(app) as c:
        yield c


def signup(client, role, email, name="Test User"):
    r = client.post("/api/auth/register", json={"name": name, "email": email, "password": "secret1", "role": role})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def owner(client):
    return signup(client, "owner", "owner@example.com", "Olive Owner")


@pytest.fixture()
def student(client):
    return signup(client, "student", "student@example.com", "Sam Student")


def make_hostel(client, owner, price=None, **over):
    """Create a hostel. `price` is a shortcut for a single 'Single room' type."""
    body = {"name": "Roysambu Heights", "distance_km": 0.8, "amenities": ["WiFi", "Security"], **over}
    if "rooms" not in body:
        body["rooms"] = [{"name": "Single room", "price": price or 11000}]
    r = client.post("/api/hostels", json=body, headers=owner)
    assert r.status_code == 201, r.text
    return r.json()
