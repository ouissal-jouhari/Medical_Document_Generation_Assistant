"""F-22 : le rôle applicatif peut supprimer une consultation et ses données associées.

Revision ID: 0005
Revises: 0004
"""

from alembic import op

revision = "0005"
down_revision = "0004"

APP_ROLE = "xeleron_app"
TABLES = ("consultation", "consultation_correction", "document")


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"GRANT DELETE ON {table} TO {APP_ROLE}")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"REVOKE DELETE ON {table} FROM {APP_ROLE}")
