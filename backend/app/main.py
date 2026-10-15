import logging
import time

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .db import get_db
from .models import Appointment, Doctor
from .schemas import (
    AppointmentInput,
    AppointmentOutput,
    Department,
    DoctorInput,
    DoctorOutput,
    Status,
    Urgency,
)

app = FastAPI(title="MediQueue API", version="1.0.0")
requests = Counter("mediqueue_http_requests_total", "HTTP requests", ["method", "route", "status"])
latency = Histogram("mediqueue_http_request_duration_seconds", "HTTP latency", ["method", "route"])
logger = logging.getLogger("uvicorn.error")


@app.middleware("http")
async def observe(request, call_next):
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        # Unhandled exceptions must count toward error-rate alerts as well.
        route = request.scope.get("route")
        path = route.path if route else "unmatched"
        if path != "/metrics":
            requests.labels(request.method, path, str(status)).inc()
            latency.labels(request.method, path).observe(time.perf_counter() - started)


@app.get("/")
def root():
    return {"service": "mediqueue", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "healthy", "service": "mediqueue"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1 FROM doctors LIMIT 1"))
    except SQLAlchemyError:
        logger.warning("Database readiness check failed")
        raise HTTPException(503, "Database unavailable or migrations pending") from None
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Appointment.status, func.count()).group_by(Appointment.status)).all())
    urgent = db.scalar(
        select(func.count())
        .select_from(Appointment)
        .where(Appointment.urgency == "urgent", Appointment.status.in_(("scheduled", "checked_in")))
    )
    return {
        "total": sum(counts.values()),
        "scheduled": counts.get("scheduled", 0),
        "checked_in": counts.get("checked_in", 0),
        "completed": counts.get("completed", 0),
        "cancelled": counts.get("cancelled", 0),
        "urgent": urgent,
    }


def find_doctor(doctor_id: int, db: Session) -> Doctor:
    doctor = db.get(Doctor, doctor_id)
    if doctor is None:
        raise HTTPException(404, "Doctor not found")
    return doctor


@app.get("/api/doctors", response_model=list[DoctorOutput])
def list_doctors(
    department: Department | None = None,
    active: bool | None = None,
    db: Session = Depends(get_db),
):
    query = select(Doctor)
    if department:
        query = query.where(Doctor.department == department)
    if active is not None:
        query = query.where(Doctor.active.is_(active))
    return db.scalars(query.order_by(Doctor.full_name.asc(), Doctor.id.asc())).all()


@app.get("/api/doctors/{doctor_id}", response_model=DoctorOutput)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    return find_doctor(doctor_id, db)


@app.post("/api/doctors", response_model=DoctorOutput, status_code=201)
def create_doctor(payload: DoctorInput, db: Session = Depends(get_db)):
    doctor = Doctor(**payload.model_dump())
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


@app.put("/api/doctors/{doctor_id}", response_model=DoctorOutput)
def update_doctor(doctor_id: int, payload: DoctorInput, db: Session = Depends(get_db)):
    doctor = find_doctor(doctor_id, db)
    for key, value in payload.model_dump().items():
        setattr(doctor, key, value)
    db.commit()
    db.refresh(doctor)
    return doctor


@app.delete("/api/doctors/{doctor_id}", status_code=204)
def delete_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = find_doctor(doctor_id, db)
    booked = db.scalar(
        select(func.count()).select_from(Appointment).where(Appointment.doctor_id == doctor_id)
    )
    if booked:
        raise HTTPException(409, "Doctor has appointments; reassign or cancel them first")
    db.delete(doctor)
    db.commit()
    return Response(status_code=204)


def find_appointment(appointment_id: int, db: Session) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(404, "Appointment not found")
    return appointment


def assert_doctor_bookable(doctor_id: int, db: Session) -> None:
    doctor = db.get(Doctor, doctor_id)
    if doctor is None:
        raise HTTPException(422, "Unknown doctor_id")
    if not doctor.active:
        raise HTTPException(422, "Doctor is not accepting appointments")


@app.get("/api/appointments", response_model=list[AppointmentOutput])
def list_appointments(
    status: Status | None = None,
    department: Department | None = None,
    urgency: Urgency | None = None,
    doctor_id: int | None = Query(default=None, ge=1),
    q: str = Query(default="", max_length=120),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = select(Appointment)
    if status:
        query = query.where(Appointment.status == status)
    if urgency:
        query = query.where(Appointment.urgency == urgency)
    if department:
        query = query.where(Appointment.doctor.has(Doctor.department == department))
    if doctor_id:
        query = query.where(Appointment.doctor_id == doctor_id)
    if q:
        query = query.where(
            or_(
                Appointment.patient_name.icontains(q, autoescape=True),
                Appointment.patient_phone.icontains(q, autoescape=True),
                Appointment.reason.icontains(q, autoescape=True),
            )
        )
    return db.scalars(
        query.order_by(Appointment.scheduled_for.asc(), Appointment.id.asc()).offset(offset).limit(limit)
    ).all()


@app.get("/api/appointments/{appointment_id}", response_model=AppointmentOutput)
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    return find_appointment(appointment_id, db)


@app.post("/api/appointments", response_model=AppointmentOutput, status_code=201)
def create_appointment(payload: AppointmentInput, db: Session = Depends(get_db)):
    assert_doctor_bookable(payload.doctor_id, db)
    appointment = Appointment(**payload.model_dump())
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@app.put("/api/appointments/{appointment_id}", response_model=AppointmentOutput)
def update_appointment(
    appointment_id: int, payload: AppointmentInput, db: Session = Depends(get_db)
):
    appointment = find_appointment(appointment_id, db)
    assert_doctor_bookable(payload.doctor_id, db)
    for key, value in payload.model_dump().items():
        setattr(appointment, key, value)
    db.commit()
    db.refresh(appointment)
    return appointment


@app.delete("/api/appointments/{appointment_id}", status_code=204)
def delete_appointment(appointment_id: int, db: Session = Depends(get_db)):
    db.delete(find_appointment(appointment_id, db))
    db.commit()
    return Response(status_code=204)
