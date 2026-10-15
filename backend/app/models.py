from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Doctor(Base):
    """A clinician who can be booked for appointments."""

    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(30), index=True)
    specialization: Mapped[str] = mapped_column(String(80))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="doctor", cascade="save-update, merge"
    )


class Appointment(Base):
    """A booked patient visit. Department is owned by the doctor, not duplicated here."""

    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_name: Mapped[str] = mapped_column(String(120), index=True)
    patient_phone: Mapped[str] = mapped_column(String(20))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="scheduled", index=True)
    urgency: Mapped[str] = mapped_column(String(20), default="routine")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    doctor: Mapped[Doctor] = relationship(back_populates="appointments", lazy="joined")

    @property
    def doctor_name(self) -> str:
        return self.doctor.full_name if self.doctor is not None else ""

    @property
    def doctor_department(self) -> str:
        return self.doctor.department if self.doctor is not None else ""
