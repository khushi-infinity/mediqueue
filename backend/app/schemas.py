from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Department = Literal["general", "cardiology", "orthopedics", "pediatrics", "dermatology", "ent"]
Status = Literal["scheduled", "checked_in", "completed", "cancelled"]
Urgency = Literal["routine", "soon", "urgent"]


class DoctorInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    full_name: str = Field(min_length=3, max_length=120)
    department: Department
    specialization: str = Field(min_length=2, max_length=80)
    active: bool = True


class DoctorOutput(DoctorInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class AppointmentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    patient_name: str = Field(min_length=3, max_length=120)
    patient_phone: str = Field(min_length=6, max_length=20, pattern=r"^[0-9+\- ]+$")
    doctor_id: int = Field(ge=1)
    scheduled_for: datetime
    reason: str = Field(default="", max_length=500)
    status: Status = "scheduled"
    urgency: Urgency = "routine"
    notes: str = Field(default="", max_length=1000)


class AppointmentOutput(AppointmentInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    doctor_name: str = ""
    doctor_department: str = ""
    created_at: datetime
    updated_at: datetime
