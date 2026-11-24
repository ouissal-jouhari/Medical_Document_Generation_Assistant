"""Tables du jalon 2. Types portables (PostgreSQL en production, SQLite possible en test)."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db import Base


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
