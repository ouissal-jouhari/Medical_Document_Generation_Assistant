"""Jalon 6 : exports des documents approuvés (entité Export, F-18).

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"

APP_ROLE = "xeleron_app"


def upgrade() -> None:
    op.create_table(
        "export",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("document.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(8), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_export_document_id", "export", ["document_id"])
    # Ajout seul : DELETE uniquement pour la suppression (F-22) et la conservation (N-10).
    op.execute("REVOKE ALL ON export FROM PUBLIC")
    op.execute(f"GRANT SELECT, INSERT, DELETE ON export TO {APP_ROLE}")


def downgrade() -> None:
    op.drop_index("ix_export_document_id", table_name="export")
    op.drop_table("export")
