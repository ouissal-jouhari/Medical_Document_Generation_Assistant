"""Jalon 4 : texte de consultation et documents générés.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004"
down_revision = "0003"

APP_ROLE = "xeleron_app"
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("consultation", sa.Column("consultation_text", sa.Text(), nullable=True))
    op.add_column(
        "consultation",
        sa.Column("consultation_text_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "document",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("consultation_id", sa.Uuid(), sa.ForeignKey("consultation.id"), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("text_snapshot", sa.Text(), nullable=True),
        sa.Column("sections", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_document_consultation_id", "document", ["consultation_id"])
    op.create_index("ix_document_author_id", "document", ["author_id"])
    op.execute("REVOKE ALL ON document FROM PUBLIC")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON document TO {APP_ROLE}")


def downgrade() -> None:
    op.drop_index("ix_document_author_id", table_name="document")
    op.drop_index("ix_document_consultation_id", table_name="document")
    op.drop_table("document")
    op.drop_column("consultation", "consultation_text_updated_at")
    op.drop_column("consultation", "consultation_text")
