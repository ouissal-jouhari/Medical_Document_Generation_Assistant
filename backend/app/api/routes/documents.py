"""Routes de revue d'un document (E-06). Toutes exigent un clinicien authentifié (F-02) et ne
voient que les documents de l'auteur (F-25, H-03)."""

from uuid import UUID

from fastapi import APIRouter, Response

from app.adapters.models import DocumentVersionEvent
from app.api.deps import ClinicianUser, ExportServiceDep, ReviewServiceDep
from app.api.schemas import (
    DocumentOut,
    ExpectedVersionIn,
    MarkOut,
    MissingOut,
    RollbackIn,
    SectionsEditIn,
    VersionOut,
)
from app.domain.document import DocumentState
from app.domain.values import ExportedFile
from app.services.review import DocumentView, VersionView

router = APIRouter(prefix="/documents", tags=["documents"])


def _mark(event: DocumentVersionEvent | None) -> MarkOut | None:
    if event is None:
        return None
    return MarkOut(actor_id=event.actor_id, occurred_at=event.occurred_at)


def document_out(view: DocumentView) -> DocumentOut:
    document, current = view.document, view.current
    return DocumentOut(
        id=document.id,
        consultation_id=document.consultation_id,
        document_type=document.document_type,
        state=document.state,
        draft=document.state != DocumentState.APPROVED,
        version=document.version,
        version_kind=current.version.kind,
        restored_from=current.version.restored_from,
        version_author_id=current.version.author_id,
        version_created_at=current.version.created_at,
        reviewed=_mark(current.reviewed),
        rejected=_mark(current.rejected),
        text_snapshot=current.version.text_snapshot,
        sections=current.version.content,
        missing_information=[MissingOut(**item) for item in view.missing_information],
        created_at=document.created_at,
        approved_at=document.approved_at,
        approver_name=document.approver_name,
        approved_version=document.approved_version,
        clinic=document.clinic_snapshot,
    )


def _version_out(view: VersionView, approved_version: int | None) -> VersionOut:
    version = view.version
    return VersionOut(
        number=version.number,
        kind=version.kind,
        restored_from=version.restored_from,
        author_id=version.author_id,
        created_at=version.created_at,
        reviewed=_mark(view.reviewed),
        rejected=_mark(view.rejected),
        approved=version.number == approved_version,
        text_snapshot=version.text_snapshot,
        sections=version.content,
    )


@router.get("/{document_id}")
def get_document(document_id: UUID, user: ClinicianUser, review: ReviewServiceDep) -> DocumentOut:
    return document_out(review.view(user.id, document_id))


@router.get("/{document_id}/versions")
def list_versions(
    document_id: UUID, user: ClinicianUser, review: ReviewServiceDep
) -> list[VersionOut]:
    approved = review.view(user.id, document_id).document.approved_version
    return [_version_out(v, approved) for v in review.history(user.id, document_id)]


@router.put("/{document_id}/sections")
def edit_sections(
    document_id: UUID, body: SectionsEditIn, user: ClinicianUser, review: ReviewServiceDep
) -> DocumentOut:
    edits = {section.name: section.content for section in body.sections}
    return document_out(review.edit(user.id, document_id, body.expected_version, edits))


@router.post("/{document_id}/reject")
def reject(
    document_id: UUID, body: ExpectedVersionIn, user: ClinicianUser, review: ReviewServiceDep
) -> DocumentOut:
    return document_out(review.reject(user.id, document_id, body.expected_version))


@router.post("/{document_id}/regenerate")
def regenerate(
    document_id: UUID, body: ExpectedVersionIn, user: ClinicianUser, review: ReviewServiceDep
) -> DocumentOut:
    return document_out(review.regenerate(user.id, document_id, body.expected_version))


@router.post("/{document_id}/rollback")
def rollback(
    document_id: UUID, body: RollbackIn, user: ClinicianUser, review: ReviewServiceDep
) -> DocumentOut:
    return document_out(
        review.rollback(user.id, document_id, body.expected_version, body.to_version)
    )


@router.post("/{document_id}/review")
def mark_reviewed(
    document_id: UUID, body: ExpectedVersionIn, user: ClinicianUser, review: ReviewServiceDep
) -> DocumentOut:
    return document_out(review.mark_reviewed(user.id, document_id, body.expected_version))


@router.post("/{document_id}/approve")
def approve(
    document_id: UUID, body: ExpectedVersionIn, user: ClinicianUser, review: ReviewServiceDep
) -> DocumentOut:
    return document_out(
        review.approve(user.id, user.display_name, document_id, body.expected_version)
    )


@router.post("/{document_id}/new-document", status_code=201)
def create_new_document(
    document_id: UUID, user: ClinicianUser, review: ReviewServiceDep
) -> DocumentOut:
    document = review.create_new_document(user.id, document_id)
    return document_out(review.view_of(document))


def _download(exported: ExportedFile) -> Response:
    """Fichier téléchargé sur l'appareil local (F-18, I-06), jamais mis en cache."""
    return Response(
        content=exported.content,
        media_type=exported.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{exported.filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/{document_id}/export")
def export_pdf(document_id: UUID, user: ClinicianUser, exports: ExportServiceDep) -> Response:
    return _download(exports.export_pdf(user.id, document_id))


@router.post("/{document_id}/provenance-report")
def provenance_report(
    document_id: UUID, user: ClinicianUser, exports: ExportServiceDep
) -> Response:
    return _download(exports.provenance_report(user.id, document_id))
