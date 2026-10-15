import pytest
from sqlalchemy.exc import OperationalError

from app.db import get_db
from app.main import app, latency, requests


def test_health_ready_metrics(client):
    assert client.get("/").json()["service"] == "mediqueue"
    assert client.get("/health").json()["status"] == "healthy"
    assert client.get("/ready").status_code == 200
    assert "mediqueue_http_requests_total" in client.get("/metrics").text


def test_doctor_crud(client, doctor):
    created = client.post("/api/doctors", json=doctor)
    assert created.status_code == 201
    doctor_id = created.json()["id"]
    assert client.get(f"/api/doctors/{doctor_id}").json()["full_name"] == doctor["full_name"]
    assert len(client.get("/api/doctors?department=cardiology").json()) == 1
    assert client.get("/api/doctors?department=ent").json() == []
    assert client.get("/api/doctors?active=true").json()[0]["id"] == doctor_id
    assert client.put(f"/api/doctors/{doctor_id}", json={**doctor, "active": False}).json()["active"] is False
    assert client.delete(f"/api/doctors/{doctor_id}").status_code == 204
    assert client.get(f"/api/doctors/{doctor_id}").status_code == 404


def test_appointment_crud(client, booked, payload):
    appointment_id = booked["appointment"]["id"]
    assert booked["appointment"]["doctor_name"] == "Dr. Ananya Rao"
    assert booked["appointment"]["doctor_department"] == "cardiology"
    assert client.get(f"/api/appointments/{appointment_id}").json()["patient_name"] == payload["patient_name"]
    update = {**payload, "doctor_id": booked["doctor_id"], "status": "completed"}
    assert client.put(f"/api/appointments/{appointment_id}", json=update).json()["status"] == "completed"
    assert client.delete(f"/api/appointments/{appointment_id}").status_code == 204
    assert client.get(f"/api/appointments/{appointment_id}").status_code == 404


def test_filters_and_stats(client, doctor, payload):
    doctor_id = client.post("/api/doctors", json=doctor).json()["id"]
    first = {**payload, "doctor_id": doctor_id, "urgency": "urgent"}
    second = {
        **payload,
        "patient_name": "Priya Nair",
        "doctor_id": doctor_id,
        "status": "completed",
        "urgency": "routine",
    }
    client.post("/api/appointments", json=first)
    client.post("/api/appointments", json=second)

    assert len(client.get("/api/appointments?status=scheduled").json()) == 1
    assert len(client.get("/api/appointments?urgency=urgent").json()) == 1
    assert len(client.get("/api/appointments?department=cardiology").json()) == 2
    assert len(client.get(f"/api/appointments?doctor_id={doctor_id}").json()) == 2
    assert [row["patient_name"] for row in client.get("/api/appointments?q=nair").json()] == ["Priya Nair"]
    assert client.get("/api/stats").json() == {
        "total": 2,
        "scheduled": 1,
        "checked_in": 0,
        "completed": 1,
        "cancelled": 0,
        "urgent": 1,
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("patient_name", " "),
        ("patient_phone", "call-me"),
        ("status", "closed"),
        ("urgency", "emergency"),
        ("reason", "x" * 501),
        ("scheduled_for", "not-a-date"),
        ("unknown", "extra"),
    ],
)
def test_validation(client, booked, payload, field, value):
    body = {**payload, "doctor_id": booked["doctor_id"], field: value}
    assert client.post("/api/appointments", json=body).status_code == 422
    assert client.post("/api/doctors", json={"full_name": "Dr. Test", "department": "clinic"}).status_code == 422


def test_unknown_or_inactive_doctor_is_rejected(client, doctor, payload):
    assert client.post("/api/appointments", json={**payload, "doctor_id": 99999}).status_code == 422
    inactive = client.post("/api/doctors", json={**doctor, "active": False}).json()["id"]
    assert client.post("/api/appointments", json={**payload, "doctor_id": inactive}).status_code == 422


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_appointment(client, booked, payload, method):
    kwargs = {"json": {**payload, "doctor_id": booked["doctor_id"]}} if method == "put" else {}
    assert getattr(client, method)("/api/appointments/99999", **kwargs).status_code == 404


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_doctor(client, doctor, method):
    kwargs = {"json": doctor} if method == "put" else {}
    assert getattr(client, method)("/api/doctors/99999", **kwargs).status_code == 404


def test_doctor_with_appointments_cannot_be_deleted(client, booked):
    assert client.delete(f"/api/doctors/{booked['doctor_id']}").status_code == 409


def test_invalid_query(client):
    assert client.get("/api/appointments?limit=0").status_code == 422
    assert client.get("/api/appointments?status=anything").status_code == 422
    assert client.get("/api/appointments?department=cardiology&limit=101").status_code == 422


def test_search_escapes_wildcards(client, booked):
    assert client.get("/api/appointments?q=%25").json() == []


def test_readiness_failure(client):
    class Unavailable:
        def execute(self, query):
            raise OperationalError("SELECT", {}, Exception("offline"))

    app.dependency_overrides[get_db] = lambda: Unavailable()
    assert client.get("/ready").status_code == 503
    assert client.get("/health").status_code == 200


def test_unhandled_failure_is_counted(client):
    class Unavailable:
        def scalars(self, query):
            raise OperationalError("SELECT", {}, Exception("offline"))

    app.dependency_overrides[get_db] = lambda: Unavailable()
    counter = requests.labels("GET", "/api/appointments", "500")
    histogram = latency.labels("GET", "/api/appointments")
    before_count = counter._value.get()
    before_latency = histogram._sum.get()
    with pytest.raises(OperationalError):
        client.get("/api/appointments")
    assert counter._value.get() == before_count + 1
    assert histogram._sum.get() > before_latency


def test_metrics_use_bounded_routes_and_exclude_scrapes(client, booked):
    appointment_id = booked["appointment"]["id"]
    counter = requests.labels("GET", "/api/appointments/{appointment_id}", "200")
    before = counter._value.get()
    client.get(f"/api/appointments/{appointment_id}")
    assert counter._value.get() == before + 1
    output = client.get("/metrics").text
    # Bounded label cardinality: the route template is exported, the raw id never is.
    assert 'route="/api/appointments/{appointment_id}"' in output
    numeric_route = f'route="/api/appointments/{appointment_id}"'
    assert numeric_route not in output
    assert 'route="/metrics"' not in output


def test_invalid_update_preserves_existing_appointment(client, booked, payload):
    appointment_id = booked["appointment"]["id"]
    body = {**payload, "doctor_id": booked["doctor_id"], "patient_name": " "}
    assert client.put(f"/api/appointments/{appointment_id}", json=body).status_code == 422
    assert client.get(f"/api/appointments/{appointment_id}").json()["patient_name"] == payload["patient_name"]


def test_pagination_has_stable_order(client, doctor, payload):
    doctor_id = client.post("/api/doctors", json=doctor).json()["id"]
    ids = [
        client.post(
            "/api/appointments",
            json={
                **payload,
                "doctor_id": doctor_id,
                "patient_name": f"Patient {index}",
                "scheduled_for": f"2026-05-{(index % 28) + 1:02d}T09:00:00+05:30",
            },
        ).json()["id"]
        for index in range(15)
    ]
    first = client.get("/api/appointments?limit=13").json()
    second = client.get("/api/appointments?limit=13&offset=12").json()
    assert [row["id"] for row in first[:12]] + [row["id"] for row in second] == ids
