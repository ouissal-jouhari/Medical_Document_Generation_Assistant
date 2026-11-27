"""Export PDF d'un document approuvé et rapport de provenance (E-07 ; F-18, F-20, F-23, F-24).

Accès par le document filtré par auteur (F-25). Chaque export est enregistré (entité Export) et
tracé dans l'audit, comme chaque rapport de provenance, dans la transaction de l'action. Un échec
de rendu renvoie un message sûr ; le document reste inchangé et rien n'est tracé (N-11).
"""

from collections.abc import Callable
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.audit import SqlAuditLog
from app.adapters.models import Export, User
from app.domain import export as rules
from app.domain.audit import AuditAction
from app.domain.clock import Clock
from app.domain.errors import ExportError, ExportFailed
from app.domain.values import ExportedFile
from app.ports import DocumentExporter
from app.services.review import ReviewService

log = structlog.get_logger()

PDF_FORMAT = "pdf"


class ExportService:
    def __init__(
        self,
        session: Session,
        clock: Clock,
        review: ReviewService,
        exporter: DocumentExporter,
    ) -> None:
        self._session = session
        self._clock = clock
        self._review = review
        self._exporter = exporter
        self._audit = SqlAuditLog(clock)

    def export_pdf(self, author_id: UUID, document_id: UUID) -> ExportedFile:
        """PDF clinique, après approbation seulement (F-18), avec la clinique figée (H-02)."""
        view = self._review.view(author_id, document_id)
        document = view.document
        rules.ensure_exportable(document.state)
        if document.approved_at is None or document.approver_name is None:
            raise ExportFailed
        exportable = rules.exportable_document(
            view.current.version.content,
            document.clinic_snapshot or {},
            document.approver_name,
            document.approved_at,
        )
        filename = f"{document.document_type}-v{document.version}.pdf"
        exported = self._render(lambda: self._exporter.export(exportable, filename))
        self._session.add(
            Export(
                document_id=document.id,
                version=document.version,
                format=PDF_FORMAT,
                actor_id=author_id,
                created_at=self._clock.now(),
            )
        )
        self._audit.record(
            self._session, author_id, AuditAction.EXPORTED, document.id, document.version
        )
        self._session.flush()
        return exported

    def provenance_report(self, author_id: UUID, document_id: UUID) -> ExportedFile:
        """Rapport séparé, à la demande, avant et après approbation (F-23, L-08)."""
        view = self._review.view(author_id, document_id)
        document = view.document
        content = view.current.version.content
        report = rules.provenance_report(
            content,
            document.state,
            document.version,
            self._clock.now(),
            self._display_names(rules.clinician_ids(content)),
        )
        filename = f"provenance-{document.document_type}-v{document.version}.pdf"
        exported = self._render(lambda: self._exporter.export_provenance(report, filename))
        self._audit.record(
            self._session,
            author_id,
            AuditAction.PROVENANCE_REPORT_GENERATED,
            document.id,
            document.version,
        )
        self._session.flush()
        return exported

    def _display_names(self, ids: set[str]) -> dict[str, str]:
        if not ids:
            return {}
        users = self._session.scalars(select(User).where(User.id.in_([UUID(i) for i in ids])))
        return {str(user.id): user.display_name for user in users}

    def _render(self, render: Callable[[], ExportedFile]) -> ExportedFile:
        try:
            return render()
        except ExportError:
            # Ni contenu ni détail technique dans le journal (N-08, N-11).
            log.warning("export_failed")
            raise ExportFailed from None
