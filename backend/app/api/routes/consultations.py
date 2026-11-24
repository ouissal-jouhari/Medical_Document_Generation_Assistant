"""Routes des consultations (E-02, E-03, E-04). Toutes exigent un clinicien authentifié (F-02)
et ne voient que ses propres consultations (F-25)."""

from pathlib import PurePath
from uuid import UUID

from fastapi import APIRouter, UploadFile

from app.adapters.models import Consultation
from app.api.deps import ClinicianUser, ConsultationServiceDep
from app.api.schemas import (
    ConsultationOut,
    ConsultationSummary,
    CorrectionOut,
    IssueOut,
    SuperbillIn,
)
from app.services.consultations import ConsultationService

router = APIRouter(prefix="/consultations", tags=["consultations"])


def _out(
    service: ConsultationService, consultation: Consultation, extraction: str | None = None
) -> ConsultationOut:
    return ConsultationOut(
        id=consultation.id,
        state=consultation.state,
        created_at=consultation.created_at,
        extraction_failures=consultation.extraction_failures,
        extraction=extraction,
        data=consultation.data,
        issues=[IssueOut(field=i.field, code=i.code, blocking=i.blocking) for i in service.issues(consultation)],
        corrections=[
            CorrectionOut(field=c.field, author_id=c.author_id, changed_at=c.changed_at)
            for c in service.corrections(consultation)
        ],
    )


def _read(file: UploadFile, limit: int) -> tuple[bytes, str]:
    """Lit au plus limit+1 octets (jamais le fichier entier en mémoire) ; le nom n'est pas gardé."""
    content = file.file.read(limit + 1)
    extension = PurePath(file.filename or "").suffix
    return content, extension


@router.get("")
def list_consultations(
    user: ClinicianUser, service: ConsultationServiceDep
) -> list[ConsultationSummary]:
    return [
        ConsultationSummary(
            id=c.id,
            state=c.state,
            created_at=c.created_at,
            patient_name=((c.data or {}).get("patient") or {}).get("fullName"),
            extraction_failures=c.extraction_failures,
        )
        for c in service.list(user.id)
    ]


@router.post("", status_code=201)
def create_consultation(
    user: ClinicianUser, service: ConsultationServiceDep, file: UploadFile
) -> ConsultationOut:
    content, extension = _read(file, service.max_bytes)
    outcome = service.create(user.id, content, extension)
    return _out(service, outcome.consultation, outcome.extraction)


@router.get("/{consultation_id}")
def get_consultation(
    consultation_id: UUID, user: ClinicianUser, service: ConsultationServiceDep
) -> ConsultationOut:
    return _out(service, service.get(user.id, consultation_id))


@router.post("/{consultation_id}/superbill")
def redeposit_superbill(
    consultation_id: UUID, user: ClinicianUser, service: ConsultationServiceDep, file: UploadFile
) -> ConsultationOut:
    content, extension = _read(file, service.max_bytes)
    outcome = service.redeposit(user.id, consultation_id, content, extension)
    return _out(service, outcome.consultation, outcome.extraction)


@router.put("/{consultation_id}/data")
def correct_data(
    consultation_id: UUID, body: SuperbillIn, user: ClinicianUser, service: ConsultationServiceDep
) -> ConsultationOut:
    consultation = service.correct(user.id, consultation_id, body.model_dump(by_alias=True))
    return _out(service, consultation)


@router.post("/{consultation_id}/validate")
def validate_data(
    consultation_id: UUID, user: ClinicianUser, service: ConsultationServiceDep
) -> ConsultationOut:
    return _out(service, service.validate(user.id, consultation_id))
