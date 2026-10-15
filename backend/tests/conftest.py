import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    # CI supplies a dedicated PostgreSQL database; local unit tests use isolated memory.
    url = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    options = (
        {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool} if url == "sqlite://" else {}
    )
    engine = create_engine(url, **options)
    Base.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()

    def override():
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        transaction.rollback()
        connection.close()
        engine.dispose()


@pytest.fixture()
def doctor():
    return {
        "full_name": "Dr. Ananya Rao",
        "department": "cardiology",
        "specialization": "Interventional cardiology",
        "active": True,
    }


@pytest.fixture()
def payload():
    return {
        "patient_name": "Ravi Kumar",
        "patient_phone": "+91 98765 43210",
        "scheduled_for": "2026-05-04T10:30:00+05:30",
        "reason": "Chest pain follow-up",
        "status": "scheduled",
        "urgency": "soon",
        "notes": "Bring previous ECG reports",
    }


@pytest.fixture()
def booked(client, doctor, payload):
    """A persisted doctor plus one appointment booked with that doctor."""
    doctor_id = client.post("/api/doctors", json=doctor).json()["id"]
    response = client.post("/api/appointments", json={**payload, "doctor_id": doctor_id})
    assert response.status_code == 201
    return {"doctor_id": doctor_id, "appointment": response.json()}
