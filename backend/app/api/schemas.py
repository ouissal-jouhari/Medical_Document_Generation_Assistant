"""Schémas de l'API des consultations (contrat unique, D-06). Clés alignées sur la section 9.2."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Short = Annotated[str | None, StringConstraints(max_length=300)]
Code = Annotated[str, StringConstraints(max_length=20)]
Text = Annotated[str, StringConstraints(max_length=500)]


class _In(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class PatientIn(_In):
    full_name: Short = Field(default=None, alias="fullName")
    date_of_birth: Short = Field(default=None, alias="dateOfBirth")
    patient_id: Short = Field(default=None, alias="patientId")


class PhysicianIn(_In):
    name: Short = None


class EncounterIn(_In):
    date_of_service: Short = Field(default=None, alias="dateOfService")
    place_of_service: Short = Field(default=None, alias="placeOfService")


class DiagnosisIn(_In):
    code: Code = ""
    description: Text = ""


class ProcedureIn(_In):
    code: Code = ""
    description: Text = ""
    units: int | None = Field(default=None, ge=-100000, le=100000)


class BillingIn(_In):
    total_charges: Short = Field(default=None, alias="totalCharges")


class SuperbillIn(_In):
    patient: PatientIn = PatientIn()
    physician: PhysicianIn = PhysicianIn()
    encounter: EncounterIn = EncounterIn()
    diagnoses: Annotated[list[DiagnosisIn], Field(max_length=50)] = []
    procedures: Annotated[list[ProcedureIn], Field(max_length=50)] = []
    billing: BillingIn = BillingIn()


class IssueOut(BaseModel):
    field: str
    code: str
    blocking: bool


class CorrectionOut(BaseModel):
    field: str
    author_id: UUID
    changed_at: datetime


class ConsultationSummary(BaseModel):
    id: UUID
    state: str
    created_at: datetime
    patient_name: str | None
    extraction_failures: int


class ConsultationOut(BaseModel):
    id: UUID
    state: str
    created_at: datetime
    extraction_failures: int
    extraction: str | None = None
    data: dict[str, Any] | None
    issues: list[IssueOut]
    corrections: list[CorrectionOut]
