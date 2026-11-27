"""F-05 sur PostgreSQL : modèles et migration 0003 concordent ; corrections sans UPDATE."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.adapters.icd_table import load_known_icd
from app.adapters.models import Consultation, ConsultationCorrection
from app.adapters.storage import LocalFileStore
from app.domain.clock import FixedClock
from app.services.consultations import ConsultationService
from tests.conftest import SwitchableOcr
from tests.superbill_samples import CLEAN_TEXT, EXPECTED_CLEAN, pdf_with_text


def test_F05_full_flow_runs_on_postgres_with_the_application_role(
    migrated: dict[str, str], tmp_path: Path
) -> None:
    engine = sa.create_engine(migrated["app"])
    clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    ocr = SwitchableOcr(CLEAN_TEXT)
    author = uuid4()
    with Session(engine) as session:
        service = ConsultationService(
            session, clock, ocr, LocalFileStore(str(tmp_path)), load_known_icd(), 50 * 1024 * 1024
        )
        outcome = service.create(author, pdf_with_text(CLEAN_TEXT), "pdf")
        consultation_id = outcome.consultation.id
        assert outcome.consultation.data == EXPECTED_CLEAN
        body = {**EXPECTED_CLEAN, "patient": {**EXPECTED_CLEAN["patient"], "fullName": "Jane Roe"}}
        service.correct(author, consultation_id, body)
        service.validate(author, consultation_id)
        session.commit()
    with Session(engine) as session:
        stored = session.get(Consultation, consultation_id)
        assert stored is not None and stored.state == "validated"
        assert stored.data is not None and stored.data["patient"]["fullName"] == "Jane Roe"
        assert stored.extracted_data == EXPECTED_CLEAN  # l'extraction d'origine reste intacte
        corrections = session.scalars(sa.select(ConsultationCorrection)).all()
        assert [c.field for c in corrections] == ["patient.fullName"]
        assert (corrections[0].old_value, corrections[0].new_value) == ("Jane Doe", "Jane Roe")
    engine.dispose()


def test_F05_corrections_are_append_only_for_the_application_role(
    migrated: dict[str, str],
) -> None:
    engine = sa.create_engine(migrated["app"])
    consultation_id = uuid4()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with Session(engine) as session:
        session.add(
            Consultation(
                id=consultation_id,
                author_id=uuid4(),
                state="parsed",
                file_kind="pdf",
                file_size=1,
                extraction_failures=0,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            ConsultationCorrection(
                consultation_id=consultation_id,
                author_id=uuid4(),
                field="patient.fullName",
                old_value="a",
                new_value="b",
                changed_at=now,
            )
        )
        session.commit()
    with Session(engine) as session, pytest.raises(ProgrammingError) as error:
        session.execute(sa.update(ConsultationCorrection).values(new_value="x"))
    assert "permission denied" in str(error.value)
    engine.dispose()


def test_F22_application_role_can_delete_consultation_data_but_not_audit_rows(
    migrated: dict[str, str],
) -> None:
    engine = sa.create_engine(migrated["app"])
    with Session(engine) as session:
        session.execute(sa.delete(ConsultationCorrection))
        session.execute(sa.delete(Consultation))
        session.commit()
    with Session(engine) as session, pytest.raises(ProgrammingError) as error:
        session.execute(sa.text("DELETE FROM audit_event"))
    assert "permission denied" in str(error.value)
    engine.dispose()
