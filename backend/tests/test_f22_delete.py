"""F-22 : suppression manuelle d'une consultation, avec trace minimale sans donnée patient."""

from copy import deepcopy
from uuid import UUID

import pytest
from sqlalchemy import select

from app.adapters.models import (
    AuditEventRow,
    Consultation,
    ConsultationCorrection,
    Document,
    DocumentVersion,
)
from app.api.deps import get_file_store
from tests.conftest import CANARY, Api
from tests.superbill_samples import CLEAN_TEXT, EXPECTED_CLEAN, pdf_with_text
from tests.test_consultations_api import _edit
from tests.test_generation_jalon4 import _with_llm


def _consultation_with_everything(api: Api) -> str:
    _with_llm(api).result = {"sections": []}
    api.ocr.text = CLEAN_TEXT
    upload = api.client.post(
        "/consultations",
        files={"file": ("superbill.pdf", pdf_with_text(CLEAN_TEXT))},
        headers=api.headers(),
    )
    consultation_id = str(upload.json()["id"])
    body = deepcopy(_edit(EXPECTED_CLEAN))
    body["patient"]["fullName"] = "Jane Roe"
    assert (
        api.client.put(
            f"/consultations/{consultation_id}/data", json=body, headers=api.headers()
        ).status_code
        == 200
    )
    api.client.post(f"/consultations/{consultation_id}/validate", headers=api.headers())
    api.client.put(
        f"/consultations/{consultation_id}/text",
        json={"text": f"Cough for two days. {CANARY}"},
        headers=api.headers(),
    )
    generated = api.client.post(
        f"/consultations/{consultation_id}/documents",
        json={"documentType": "clinical_note"},
        headers=api.headers(),
    )
    assert generated.status_code == 201
    return consultation_id


def test_F22_deletion_removes_everything_and_keeps_a_minimal_audit_trace(api: Api) -> None:
    consultation_id = _consultation_with_everything(api)
    with api.session() as session:
        key = session.scalars(select(Consultation.storage_key)).one()
    assert key and get_file_store().read(key)

    response = api.client.delete(f"/consultations/{consultation_id}", headers=api.headers())
    assert response.status_code == 204

    assert (
        api.client.get(f"/consultations/{consultation_id}", headers=api.headers()).status_code
        == 404
    )
    with api.session() as session:
        assert session.scalars(select(Consultation)).all() == []
        assert session.scalars(select(Document)).all() == []
        assert session.scalars(select(DocumentVersion)).all() == []
        assert session.scalars(select(ConsultationCorrection)).all() == []
        events = session.scalars(select(AuditEventRow)).all()
    with pytest.raises(FileNotFoundError):
        get_file_store().read(key)
    deleted = [e for e in events if e.action == "consultation_deleted"]
    assert len(deleted) == 1
    assert deleted[0].document_id is None and deleted[0].version is None
    assert any(e.action == "generated" for e in events)  # l'audit existant est intact
    dumped = repr([(e.actor_id, e.action, e.document_id, e.version) for e in events])
    for private in (CANARY, "Jane", consultation_id):
        assert private not in dumped


def test_F22_clinician_cannot_delete_a_foreign_or_missing_consultation(api: Api) -> None:
    consultation_id = _consultation_with_everything(api)
    other = api.headers(subject="clin-other")
    foreign = api.client.delete(f"/consultations/{consultation_id}", headers=other)
    missing = api.client.delete(f"/consultations/{UUID(int=1)}", headers=other)
    assert (foreign.status_code, foreign.json()) == (missing.status_code, missing.json())
    assert foreign.status_code == 404
    assert (
        api.client.get(f"/consultations/{consultation_id}", headers=api.headers()).status_code
        == 200
    )


def test_F22_deletion_requires_authentication(api: Api) -> None:
    assert api.client.delete(f"/consultations/{UUID(int=1)}").status_code == 401
