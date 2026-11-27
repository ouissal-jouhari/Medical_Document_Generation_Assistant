"""Jalon 5 : versions immuables, marques de revue, approbation et instantané de la clinique.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006"
down_revision = "0005"

APP_ROLE = "xeleron_app"
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "document_version",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("document.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("restored_from", sa.Integer(), nullable=True),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("text_snapshot", sa.Text(), nullable=True),
        sa.Column("content", JSON_TYPE, nullable=False),
        sa.UniqueConstraint("document_id", "number", name="uq_document_version"),
    )
    op.create_index("ix_document_version_document_id", "document_version", ["document_id"])
    op.create_table(
        "document_version_event",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("document.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("mark", sa.String(16), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_document_version_event_document_id", "document_version_event", ["document_id"]
    )
    # Chaque document existant (jalon 4) devient sa version 1, générée par l'IA.
    op.execute(
        "INSERT INTO document_version "
        "(id, document_id, number, kind, author_id, created_at, text_snapshot, content) "
        "SELECT id, id, 1, 'ai_generated', author_id, created_at, text_snapshot, sections "
        "FROM document"
    )
    op.execute("UPDATE document SET version = 1")
    op.drop_column("document", "sections")
    op.drop_column("document", "text_snapshot")
    op.add_column("document", sa.Column("approved_at", sa.DateTime(timezone=True)))
    op.add_column("document", sa.Column("approved_by", sa.Uuid()))
    op.add_column("document", sa.Column("approver_name", sa.String(255)))
    op.add_column("document", sa.Column("approved_version", sa.Integer()))
    op.add_column("document", sa.Column("clinic_snapshot", JSON_TYPE))
    # Versions et marques : ajout seul (DELETE uniquement pour la suppression F-22).
    for table in ("document_version", "document_version_event"):
        op.execute(f"REVOKE ALL ON {table} FROM PUBLIC")
        op.execute(f"GRANT SELECT, INSERT, DELETE ON {table} TO {APP_ROLE}")


def downgrade() -> None:
    for column in (
        "clinic_snapshot",
        "approved_version",
        "approver_name",
        "approved_by",
        "approved_at",
    ):
        op.drop_column("document", column)
    op.add_column("document", sa.Column("text_snapshot", sa.Text(), nullable=True))
    op.add_column("document", sa.Column("sections", JSON_TYPE, nullable=True))
    op.execute(
        "UPDATE document SET sections = v.content, text_snapshot = v.text_snapshot "
        "FROM document_version v WHERE v.document_id = document.id AND v.number = 1"
    )
    op.drop_index("ix_document_version_event_document_id", table_name="document_version_event")
    op.drop_table("document_version_event")
    op.drop_index("ix_document_version_document_id", table_name="document_version")
    op.drop_table("document_version")
