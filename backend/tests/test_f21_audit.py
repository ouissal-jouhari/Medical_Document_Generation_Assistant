"""F-20 / F-21 : audit en ajout seul, garanti par la base, écrit dans la transaction de l'action."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.adapters.audit import SqlAuditLog, purge_audit_before
from app.adapters.models import AuditEventRow, User
from app.domain.audit import AuditAction
from app.domain.clock import FixedClock
from tests.conftest import Api
from tests.helpers_routes import api_routes


def test_F20_event_has_actor_action_date_document_and_version(api: Api) -> None:
    clock = FixedClock(datetime(2026, 3, 1, 10, 0, tzinfo=UTC))
    actor, document = uuid4(), uuid4()
    with api.session() as session:
        SqlAuditLog(clock).record(session, actor, AuditAction.APPROVED, document, 3)
        session.commit()
        row = session.scalars(select(AuditEventRow)).one()
    assert (row.actor_id, row.action, row.document_id, row.version) == (
        actor,
        "approved",
        document,
        3,
    )
    assert row.occurred_at.replace(tzinfo=UTC) == clock.now()


def test_F20_all_required_actions_exist() -> None:
    assert {a.value for a in AuditAction} == {
        "generated",
        "reviewed",
        "approved",
        "rejected",
        "rollback",
        "exported",
        "provenance_report_generated",
    }


def test_F21_audit_is_written_in_the_same_transaction_as_the_action(api: Api) -> None:
    audit = SqlAuditLog(api.clock)
    with api.session() as session:
        user = User(subject="s1", display_name="A", created_at=api.clock.now())
        session.add(user)
        session.flush()
        audit.record(session, user.id, AuditAction.GENERATED)
        session.rollback()
        assert session.scalars(select(AuditEventRow)).all() == []
        assert session.scalars(select(User)).all() == []
    with api.session() as session:
        user = User(subject="s2", display_name="B", created_at=api.clock.now())
        session.add(user)
        session.flush()
        audit.record(session, user.id, AuditAction.GENERATED)
        session.commit()
        assert len(session.scalars(select(AuditEventRow)).all()) == 1


def test_F21_no_route_can_read_modify_or_delete_audit_events(api: Api) -> None:
    routes = api_routes(api.app)
    assert len(routes) >= 2  # le parcours n'est pas vide
    for route, _ in routes:
        assert "audit" not in route.path.lower(), route.path


def test_F21_audit_has_no_foreign_key_to_documents(api: Api) -> None:
    assert sa.inspect(api.engine).get_foreign_keys("audit_event") == []


def _insert_event(session: Session) -> None:
    session.execute(
        sa.insert(AuditEventRow).values(
            id=uuid4(),
            occurred_at=datetime(2025, 1, 1, tzinfo=UTC),
            actor_id=uuid4(),
            action="generated",
        )
    )


def test_F21_application_role_can_insert_but_not_update_or_delete(
    migrated: dict[str, str],
) -> None:
    engine = sa.create_engine(migrated["app"])
    with Session(engine) as session:
        _insert_event(session)
        session.commit()
        assert session.scalars(select(AuditEventRow)).one() is not None
    for statement in (
        sa.update(AuditEventRow).values(action="approved"),
        sa.delete(AuditEventRow),
    ):
        with Session(engine) as session, pytest.raises(ProgrammingError) as error:
            session.execute(statement)
        assert "permission denied" in str(error.value)
    with engine.connect() as conn, pytest.raises(ProgrammingError):
        conn.execute(sa.text("TRUNCATE audit_event"))
    engine.dispose()


def test_F21_purge_role_can_delete_old_events_but_not_update(migrated: dict[str, str]) -> None:
    app_engine = sa.create_engine(migrated["app"])
    with Session(app_engine) as session:
        _insert_event(session)
        session.commit()
    purge_engine = sa.create_engine(migrated["purge"])
    with Session(purge_engine) as session, pytest.raises(ProgrammingError):
        session.execute(sa.update(AuditEventRow).values(action="x"))
    clock = FixedClock(datetime(2026, 6, 1, tzinfo=UTC))
    with Session(purge_engine) as session:
        deleted = purge_audit_before(session, clock.now() - timedelta(days=365))
        session.commit()
    assert deleted == 1
    app_engine.dispose()
    purge_engine.dispose()


def test_F21_application_role_cannot_create_or_alter_tables(migrated: dict[str, str]) -> None:
    engine = sa.create_engine(migrated["app"])
    with engine.connect() as conn, pytest.raises(ProgrammingError):
        conn.execute(sa.text("ALTER TABLE audit_event ADD COLUMN x int"))
    engine.dispose()
