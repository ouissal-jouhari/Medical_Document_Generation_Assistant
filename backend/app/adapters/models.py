"""Tables du jalon 2. Types portables (PostgreSQL en production, SQLite possible en test)."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db import Base

JsonType = JSON().with_variant(JSONB(), "postgresql")


class User(Base):
    __tablename__ = "app_user"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    subject: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditEventRow(Base):
    """Ajout seul : UPDATE et DELETE sont retirés au rôle applicatif par la migration 0002.

    Aucune clé étrangère vers Document : l'audit survit à la suppression d'un document (F-22).
    """

    __tablename__ = "audit_event"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    actor_id: Mapped[UUID] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(64))
    document_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Consultation(Base):
    """Consultation : Superbill déposée, données extraites et corrigées, état (SRS 9.1).

    Le nom du fichier d'origine n'est pas conservé. Accès uniquement via
    AuthorScopedRepository (filtre par auteur, F-25).
    """

    __tablename__ = "consultation"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    author_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    state: Mapped[str] = mapped_column(String(16))
    storage_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_kind: Mapped[str] = mapped_column(String(8))
    file_size: Mapped[int] = mapped_column(Integer)
    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    data: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    extraction_failures: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consultation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    consultation_text_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Document(Base):
    """Document d'une consultation (SRS 9.1). `version` est le numéro de la version courante.

    Les champs d'approbation (approbateur, instantané de la clinique) sont écrits une seule
    fois, à l'approbation (F-17, H-02) ; le domaine refuse ensuite toute modification.
    """

    __tablename__ = "document"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    consultation_id: Mapped[UUID] = mapped_column(ForeignKey("consultation.id"), index=True)
    author_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    document_type: Mapped[str] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(16), default="under_review")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    approver_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clinic_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)

    # Verrou optimiste : chaque UPDATE porte « WHERE version = <version lue> » (F-14).
    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}


class DocumentVersion(Base):
    """Version immuable (F-14) : le rôle applicatif n'a ni UPDATE ni DELETE hors F-22.

    Contrainte d'unicité (document, numéro) : deux éditions concurrentes ne peuvent pas créer
    la même version.
    """

    __tablename__ = "document_version"
    __table_args__ = (UniqueConstraint("document_id", "number", name="uq_document_version"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("document.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))
    restored_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    author_id: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    text_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[dict[str, Any]] = mapped_column(JsonType)


class DocumentVersionEvent(Base):
    """Marque « relu » ou « rejeté » posée sur une version (F-15, F-26). Ajout seul."""

    __tablename__ = "document_version_event"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("document.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    mark: Mapped[str] = mapped_column(String(16))
    actor_id: Mapped[UUID] = mapped_column(Uuid)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Export(Base):
    """Export d'un document approuvé (SRS 9.1, F-18) : format, version, acteur et date.

    Ajout seul ; DELETE uniquement pour la suppression et la conservation (F-22, N-10).
    """

    __tablename__ = "export"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("document.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    format: Mapped[str] = mapped_column(String(8))
    actor_id: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConsultationCorrection(Base):
    """Correction d'un champ : auteur et date (F-05). Ajout seul : ni UPDATE ni DELETE."""

    __tablename__ = "consultation_correction"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    consultation_id: Mapped[UUID] = mapped_column(ForeignKey("consultation.id"), index=True)
    author_id: Mapped[UUID] = mapped_column(Uuid)
    field: Mapped[str] = mapped_column(String(128))
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
