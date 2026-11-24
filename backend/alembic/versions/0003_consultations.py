"""Consultations et corrections (jalon 3).

Revision ID: 0003
Revises: 0002

Droits : l'application lit, crée et modifie les consultations ; les corrections sont en ajout
seul (SELECT et INSERT). Le DELETE d'une consultation et de ses corrections est accordé au
jalon 6 (suppression, F-22).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"

APP_ROLE = "xeleron_app"
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "consultation",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("storage_key", sa.String(64), nullable=True),
        sa.Column("file_kind", sa.String(8), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("extracted_data", JSON_TYPE, nullable=True),
        sa.Column("data", JSON_TYPE, nullable=True),
        sa.Column("extraction_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_consultation_author_id", "consultation", ["author_id"])
    op.create_table(
        "consultation_correction",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("consultation_id", sa.Uuid(), sa.ForeignKey("consultation.id"), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("field", sa.String(128), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_consultation_correction_consultation_id", "consultation_correction", ["consultation_id"]
    )
    op.execute("REVOKE ALL ON consultation, consultation_correction FROM PUBLIC")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON consultation TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT ON consultation_correction TO {APP_ROLE}")


def downgrade() -> None:
    op.drop_table("consultation_correction")
    op.drop_table("consultation")
