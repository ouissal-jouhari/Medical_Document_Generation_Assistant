"""Revue d'un document (E-06) : édition, rejet, régénération, rollback, relu, approbation.

Les règles sont celles du domaine (`app.domain.document`) ; ce service charge l'état, applique
la règle, puis écrit une nouvelle version, une marque ou l'approbation, avec l'audit (F-20)
dans la même transaction. Tout accès passe par le document filtré par auteur (F-25, H-03).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.adapters.audit import SqlAuditLog
from app.adapters.models import Document, DocumentVersion, DocumentVersionEvent
from app.domain import document as rules
from app.domain.audit import AuditAction
from app.domain.clinic import ClinicProfile
from app.domain.clock import Clock
from app.domain.document import DocumentState, ReviewSnapshot, VersionKind, VersionMark
from app.domain.errors import NotFound, VersionConflict, WrongState
from app.services.generation import GenerationService

T = TypeVar("T")


@dataclass(frozen=True)
class VersionView:
    version: DocumentVersion
    marks: dict[str, DocumentVersionEvent]

    @property
    def reviewed(self) -> DocumentVersionEvent | None:
        return self.marks.get(VersionMark.REVIEWED.value)

    @property
    def rejected(self) -> DocumentVersionEvent | None:
        return self.marks.get(VersionMark.REJECTED.value)


@dataclass(frozen=True)
class DocumentView:
    document: Document
    current: VersionView

    @property
    def snapshot(self) -> ReviewSnapshot:
        return ReviewSnapshot(
            state=DocumentState(self.document.state),
            current_version=self.document.version,
            current_reviewed=self.current.reviewed is not None,
            current_rejected=self.current.rejected is not None,
        )

    @property
    def missing_information(self) -> list[dict[str, str]]:
        return rules.missing_information(self.current.version.content)


class ReviewService:
    def __init__(
        self,
        session: Session,
        clock: Clock,
        generation: GenerationService,
        clinic: ClinicProfile,
    ) -> None:
        self._session = session
        self._clock = clock
        self._generation = generation
        self._clinic = clinic
        self._audit = SqlAuditLog(clock)

    # Lecture

    def view(self, author_id: UUID, document_id: UUID) -> DocumentView:
        return self.view_of(self._generation.get_document(author_id, document_id))

    def view_of(self, document: Document) -> DocumentView:
        versions = self._versions(document)
        current = next((v for v in versions if v.version.number == document.version), None)
        if current is None:
            raise NotFound
        return DocumentView(document, current)

    def history(self, author_id: UUID, document_id: UUID) -> list[VersionView]:
        """Historique des versions, la plus récente d'abord (cas d'usage « View the version
        history »)."""
        document = self._generation.get_document(author_id, document_id)
        return sorted(self._versions(document), key=lambda v: v.version.number, reverse=True)

    def _versions(self, document: Document) -> list[VersionView]:
        versions = self._session.scalars(
            select(DocumentVersion).where(DocumentVersion.document_id == document.id)
        ).all()
        events = self._session.scalars(
            select(DocumentVersionEvent).where(DocumentVersionEvent.document_id == document.id)
        ).all()
        return [
            VersionView(v, {e.mark: e for e in events if e.version == v.number}) for v in versions
        ]

    # Actions

    def edit(
        self,
        author_id: UUID,
        document_id: UUID,
        expected_version: int,
        edits: dict[str, str | None],
    ) -> DocumentView:
        """Une seule version « edited » par enregistrement explicite (F-14)."""
        view = self.view(author_id, document_id)
        rules.ensure_modifiable(view.snapshot, expected_version)
        content = rules.apply_edits(
            view.current.version.content, edits, author_id, self._clock.now()
        )
        if content is None:
            return view
        return self._new_version(
            view, author_id, VersionKind.EDITED, content, view.current.version.text_snapshot
        )

    def reject(self, author_id: UUID, document_id: UUID, expected_version: int) -> DocumentView:
        """La version rejetée est conservée et marquée (F-15)."""
        view = self.view(author_id, document_id)
        rules.ensure_can_reject(view.snapshot, expected_version)
        self._mark(view.document, VersionMark.REJECTED, author_id)
        self._audit.record(
            self._session, author_id, AuditAction.REJECTED, view.document.id, expected_version
        )
        return self.view_of(view.document)

    def regenerate(self, author_id: UUID, document_id: UUID, expected_version: int) -> DocumentView:
        """Nouvelle version IA après rejet (F-15). Échec : la version courante reste intacte."""
        view = self.view(author_id, document_id)
        rules.ensure_can_regenerate(view.snapshot, expected_version)
        document = view.document
        content, text = self._generation.draft(
            author_id, document.consultation_id, document.document_type
        )
        result = self._new_version(view, author_id, VersionKind.AI_GENERATED, content, text)
        self._audit.record(
            self._session, author_id, AuditAction.GENERATED, document.id, document.version
        )
        return result

    def rollback(
        self, author_id: UUID, document_id: UUID, expected_version: int, target: int
    ) -> DocumentView:
        """Contenu d'une ancienne version copié dans une nouvelle version (F-16)."""
        view = self.view(author_id, document_id)
        rules.ensure_can_rollback(view.snapshot, expected_version, target)
        source = next(
            v.version for v in self._versions(view.document) if v.version.number == target
        )
        result = self._new_version(
            view,
            author_id,
            VersionKind.EDITED,
            source.content,
            source.text_snapshot,
            restored_from=target,
        )
        self._audit.record(
            self._session,
            author_id,
            AuditAction.ROLLBACK,
            view.document.id,
            view.document.version,
        )
        return result

    def mark_reviewed(
        self, author_id: UUID, document_id: UUID, expected_version: int
    ) -> DocumentView:
        """Enregistre auteur, version et date (F-26). Déjà relue : aucun nouvel événement."""
        view = self.view(author_id, document_id)
        rules.ensure_can_mark_reviewed(view.snapshot, expected_version)
        if view.current.reviewed is None:
            self._mark(view.document, VersionMark.REVIEWED, author_id)
            self._audit.record(
                self._session, author_id, AuditAction.REVIEWED, view.document.id, expected_version
            )
        return self.view_of(view.document)

    def approve(
        self, author_id: UUID, approver_name: str, document_id: UUID, expected_version: int
    ) -> DocumentView:
        """Approbation par le clinicien (S-06) : version courante relue, sections obligatoires
        fournies (F-17). Instantané des coordonnées de la clinique (H-02)."""
        view = self.view(author_id, document_id)
        rules.ensure_can_approve(view.snapshot, expected_version, view.current.version.content)
        document = view.document
        document.state = DocumentState.APPROVED.value
        document.approved_at = self._clock.now()
        document.approved_by = author_id
        document.approver_name = approver_name
        document.approved_version = document.version
        document.clinic_snapshot = self._clinic.snapshot()
        self._flush(lambda: None)
        self._audit.record(
            self._session, author_id, AuditAction.APPROVED, document.id, document.version
        )
        return self.view_of(document)

    def create_new_document(self, author_id: UUID, document_id: UUID) -> Document:
        """Correction après approbation (F-19, P14) : régénération d'un document du même type ;
        l'ancien reste figé et inchangé."""
        document = self._generation.get_document(author_id, document_id)
        if document.state != DocumentState.APPROVED.value:
            raise WrongState
        return self._generation.generate(
            author_id, document.consultation_id, document.document_type
        )

    # Écritures

    def _new_version(
        self,
        view: DocumentView,
        author_id: UUID,
        kind: VersionKind,
        content: dict[str, Any],
        text: str | None,
        restored_from: int | None = None,
    ) -> DocumentView:
        document = view.document
        document.version = view.snapshot.current_version + 1

        def write() -> None:
            self._generation.add_version(document, author_id, kind, content, text, restored_from)

        self._flush(write)
        return self.view_of(document)

    def _mark(self, document: Document, mark: VersionMark, actor_id: UUID) -> None:
        self._session.add(
            DocumentVersionEvent(
                document_id=document.id,
                version=document.version,
                mark=mark.value,
                actor_id=actor_id,
                occurred_at=self._clock.now(),
            )
        )
        self._session.flush()

    def _flush(self, write: Callable[[], T]) -> T:
        """Écriture concurrente (verrou optimiste ou unicité document/numéro) : refusée."""
        try:
            result = write()
            self._session.flush()
        except (StaleDataError, IntegrityError) as error:
            raise VersionConflict from error
        return result
