"""Insert clearly synthetic clinic data through the real API."""
import argparse
import json
import urllib.request
from urllib.parse import urlsplit, urlunsplit

DOCTORS = [
    ("Dr. Ananya Rao", "cardiology", "Interventional cardiology"),
    ("Dr. Vikram Shetty", "orthopedics", "Joint replacement surgery"),
    ("Dr. Fatima Sheikh", "pediatrics", "Neonatal and adolescent care"),
    ("Dr. Daniel Fernandes", "general", "Family medicine"),
    ("Dr. Nisha Kulkarni", "dermatology", "Clinical dermatology"),
    ("Dr. Imran Qureshi", "ent", "Rhinology and sinus surgery"),
]

# (patient, phone, department, scheduled_for, reason, urgency, status, notes)
APPOINTMENTS = [
    ("Ravi Kumar", "+91 98765 43210", "cardiology", "2026-05-04T10:30:00+05:30",
     "Chest pain follow-up", "urgent", "scheduled", "Bring previous ECG reports"),
    ("Priya Nair", "+91 98220 11223", "pediatrics", "2026-05-04T11:15:00+05:30",
     "Routine vaccination", "routine", "scheduled", "Second dose of the schedule"),
    ("Arjun Menon", "+91 90045 78120", "orthopedics", "2026-05-04T12:00:00+05:30",
     "Knee pain after football", "soon", "checked_in", "Left knee, no swelling"),
    ("Sana Qureshi", "+91 99887 66554", "dermatology", "2026-05-04T14:30:00+05:30",
     "Persistent skin rash", "routine", "scheduled", "Started two weeks ago"),
    ("Meera Iyer", "+91 98333 21190", "general", "2026-05-05T09:00:00+05:30",
     "Annual health check", "routine", "scheduled", "Fasting bloods already done"),
    ("Kabir Das", "+91 97456 33221", "ent", "2026-05-05T10:45:00+05:30",
     "Blocked left nostril", "soon", "completed", "Advised a nasal spray"),
    ("Nisha Sharma", "+91 96234 55098", "cardiology", "2026-05-05T11:30:00+05:30",
     "Palpitations while walking", "urgent", "scheduled", "Wears a fitness tracker"),
    ("Dev Patel", "+91 94567 88231", "orthopedics", "2026-05-05T15:15:00+05:30",
     "Physiotherapy review", "routine", "completed", "Range of motion improved"),
    ("Aisha Khan", "+91 99001 23456", "pediatrics", "2026-05-06T09:30:00+05:30",
     "Fever for three days", "soon", "scheduled", "Temperature log attached"),
    ("Rohan Mehta", "+91 98712 44556", "dermatology", "2026-05-06T16:00:00+05:30",
     "Follow-up on eczema", "routine", "cancelled", "Patient rescheduled by phone"),
]


def client(url: str) -> tuple[str, dict]:
    parsed = urlsplit(url)
    headers = {"Content-Type": "application/json"}
    if parsed.hostname and parsed.hostname.endswith(".localhost"):
        headers["Host"] = parsed.netloc
        url = urlunsplit(parsed._replace(netloc=f"127.0.0.1:{parsed.port or 80}"))
    return url, headers


def call(url: str, headers: dict, path: str, body: dict | None = None, method: str = "GET"):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        return None if response.status == 204 else json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:3000")
    args = parser.parse_args()
    base, headers = client(args.url)

    roster = {doctor["full_name"]: doctor["id"] for doctor in call(base, headers, "/api/doctors")}
    created_doctors = 0
    for full_name, department, specialization in DOCTORS:
        if full_name in roster:
            continue
        doctor = call(base, headers, "/api/doctors", {
            "full_name": full_name, "department": department,
            "specialization": specialization, "active": True,
        }, method="POST")
        roster[full_name] = doctor["id"]
        created_doctors += 1

    by_department = {}
    for full_name, department, _ in DOCTORS:
        by_department.setdefault(department, roster[full_name])

    existing = {row["patient_name"] for row in call(base, headers, "/api/appointments?limit=100")}
    created_appointments = 0
    for patient, phone, department, scheduled_for, reason, urgency, status, notes in APPOINTMENTS:
        if patient in existing:
            continue
        call(base, headers, "/api/appointments", {
            "patient_name": patient, "patient_phone": phone, "doctor_id": by_department[department],
            "scheduled_for": scheduled_for, "reason": reason, "urgency": urgency, "status": status,
            "notes": notes,
        }, method="POST")
        created_appointments += 1

    print(f"Created {created_doctors} doctors and {created_appointments} appointments at {args.url}")


if __name__ == "__main__":
    main()
