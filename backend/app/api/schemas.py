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
    consultation_text: str | None = None
    consultation_text_updated_at: datetime | None = None


class ConsultationTextIn(_In):
    text: Annotated[str | None, StringConstraints(max_length=5000)] = None


class DocumentGenerateIn(_In):
    document_type: str = Field(alias="documentType")


class MarkOut(BaseModel):
    actor_id: UUID
    occurred_at: datetime


class VersionOut(BaseModel):
    number: int
    kind: str
    restored_from: int | None
    author_id: UUID
    created_at: datetime
    reviewed: MarkOut | None
    rejected: MarkOut | None
    approved: bool
    text_snapshot: str | None
    sections: dict[str, Any]


class MissingOut(BaseModel):
    name: str
    level: str


class DocumentOut(BaseModel):
    """Document et sa version courante. `version`, `text_snapshot` et `sections` sont ceux de
    la version courante. `draft` vaut vrai tant que le document n'est pas approuvé (S-01)."""

    id: UUID
    consultation_id: UUID
    document_type: str
    state: str
    draft: bool
    version: int
    version_kind: str
    restored_from: int | None
    version_author_id: UUID
    version_created_at: datetime
    reviewed: MarkOut | None
    rejected: MarkOut | None
    text_snapshot: str | None
    sections: dict[str, Any]
    missing_information: list[MissingOut]
    created_at: datetime
    approved_at: datetime | None
    approver_name: str | None
    approved_version: int | None
    clinic: dict[str, Any] | None


class ExpectedVersionIn(_In):
    """Numéro de la version affichée : refus si le document a changé entre-temps (F-14)."""

    expected_version: int = Field(alias="expectedVersion", ge=1)


class SectionEditIn(_In):
    name: Annotated[str, StringConstraints(max_length=200)]
    content: Annotated[str | None, StringConstraints(max_length=10000)] = None


class SectionsEditIn(ExpectedVersionIn):
    sections: Annotated[list[SectionEditIn], Field(min_length=1, max_length=50)]


class RollbackIn(ExpectedVersionIn):
    to_version: int = Field(alias="toVersion", ge=1)
