"""Routes des consultations (E-02, E-03, E-04). Toutes exigent un clinicien authentifié (F-02)
et ne voient que ses propres consultations (F-25)."""

from pathlib import PurePath
from uuid import UUID

from fastapi import APIRouter, UploadFile

from app.adapters.models import Consultation, Document
from app.api.deps import (
    ClinicianUser,
    ConsultationServiceDep,
    GenerationServiceDep,
)
from app.api.schemas import (
    ConsultationOut,
    ConsultationSummary,
    ConsultationTextIn,
    CorrectionOut,
    DocumentGenerateIn,
    DocumentOut,
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
        issues=[
            IssueOut(field=i.field, code=i.code, blocking=i.blocking)
            for i in service.issues(consultation)
        ],
        corrections=[
            CorrectionOut(field=c.field, author_id=c.author_id, changed_at=c.changed_at)
            for c in service.corrections(consultation)
        ],
        consultation_text=consultation.consultation_text,
        consultation_text_updated_at=consultation.consultation_text_updated_at,
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
        for c in service.list_for_author(user.id)
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


@router.put("/{consultation_id}/text")
def save_consultation_text(
    consultation_id: UUID,
    body: ConsultationTextIn,
    user: ClinicianUser,
    service: GenerationServiceDep,
) -> dict[str, object]:
    consultation = service.set_text(user.id, consultation_id, body.text)
    return {
        "id": consultation.id,
        "consultation_text": consultation.consultation_text,
        "consultation_text_updated_at": consultation.consultation_text_updated_at,
    }


def _document_out(document: Document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        consultation_id=document.consultation_id,
        document_type=document.document_type,
        state=document.state,
        version=document.version,
        text_snapshot=document.text_snapshot,
        sections=document.sections,
        created_at=document.created_at,
    )


@router.post("/{consultation_id}/documents", status_code=201)
def generate_document(
    consultation_id: UUID,
    body: DocumentGenerateIn,
    user: ClinicianUser,
    service: GenerationServiceDep,
) -> DocumentOut:
    document = service.generate(user.id, consultation_id, body.document_type)
    return _document_out(document)


@router.get("/{consultation_id}/documents")
def list_documents(
    consultation_id: UUID, user: ClinicianUser, service: GenerationServiceDep
) -> list[DocumentOut]:
    documents = service.list_documents(user.id, consultation_id)
    return [_document_out(document) for document in documents]


@router.get("/documents/{document_id}")
def get_document(
    document_id: UUID, user: ClinicianUser, service: GenerationServiceDep
) -> DocumentOut:
    return _document_out(service.get_document(user.id, document_id))
