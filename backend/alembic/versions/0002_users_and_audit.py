"""Utilisateurs, audit en ajout seul et rôles de base distincts.

Revision ID: 0002
Revises: 0001

Les migrations s'exécutent avec le propriétaire de la base. L'application se connecte avec
xeleron_app, qui n'a ni UPDATE ni DELETE sur audit_event. La purge (N-10) utilise xeleron_purge,
qui peut seulement lire et supprimer.
"""

import os

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"

APP_ROLE = "xeleron_app"
PURGE_ROLE = "xeleron_purge"


def _password(variable: str) -> str:
    value = os.environ.get(variable)
    if not value:
        raise RuntimeError(f"variable d'environnement {variable} requise pour la migration")
    return value


def _ensure_role(name: str, password: str) -> None:
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :n"), {"n": name})
    verb = (
        "ALTER ROLE %I LOGIN PASSWORD %L" if exists.scalar() else "CREATE ROLE %I LOGIN PASSWORD %L"
    )
    statement = bind.execute(
        sa.text("SELECT format(:tpl, CAST(:n AS text), CAST(:p AS text))"),
        {"tpl": verb, "n": name, "p": password},
    ).scalar_one()
    bind.exec_driver_sql(statement)


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_app_user_subject", "app_user", ["subject"], unique=True)
    op.create_table(
        "audit_event",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
    )
    op.create_index("ix_audit_event_occurred_at", "audit_event", ["occurred_at"])

    _ensure_role(APP_ROLE, _password("APP_DB_PASSWORD"))
    _ensure_role(PURGE_ROLE, _password("PURGE_DB_PASSWORD"))
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}, {PURGE_ROLE}")
    op.execute("REVOKE ALL ON app_user, audit_event FROM PUBLIC")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON app_user TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT ON audit_event TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, DELETE ON audit_event TO {PURGE_ROLE}")


def downgrade() -> None:
    op.drop_table("audit_event")
    op.drop_table("app_user")
