"""Tests automatiques des exigences du jalon 6 : export PDF, provenance, suppression, conservation.

Les règles (approbation, traces, accès, échec) utilisent un faux exportateur ; le rendu réel
(texte du PDF, pagination, en-tête et pied de page, échappement) exige WeasyPrint, obligatoire
en CI (`require_weasyprint`).
"""

import io
import re
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import create_engine, select
from sqlalchemy import text as sql
from sqlalchemy.orm import Session

from app.adapters import pdf as pdf_adapter
from app.adapters.db import Base
from app.adapters.models import (
    AuditEventRow,
    Consultation,
    Document,
    DocumentVersion,
    DocumentVersionEvent,
    Export,
)
from app.adapters.storage import LocalFileStore
from app.api import main as main_module
from app.api.deps import get_clinic_profile, get_exporter, get_file_store, session_factory
from app.api.scheduler import run_retention
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.domain.clinic import ClinicProfile
from app.domain.clock import Clock, FixedClock
from app.domain.errors import ExportError
from app.domain.values import ExportableDocument, ExportedFile, ProvenanceReport
from app.services.retention import PURGE_ACTION, SYSTEM_ACTOR, RetentionService
from tests.conftest import CANARY, Api, require_weasyprint
from tests.test_generation_jalon4 import _validated
from tests.test_review_jalon5 import PLAN, _action, _approvable, _edit

DEMO = ClinicProfile(
    "XeleronIA Demo Clinic",
    "1 Example Street",
    "Springfield",
    "00000",
    "+1 555 0100",
    "contact@clinic.example",
    "https://clinic.example",
)
FORBIDDEN_IN_CLINICAL_PDF = re.compile(
    r"\b(?:AI|IA|artificial intelligence|intelligence artificielle|generated|draft|brouillon|"
    r"sources?|provenance|origins?|citations?|under review|LLM|Gemini)\b",
    re.IGNORECASE,
)


class FakeExporter:
    def __init__(self) -> None:
        self.documents: list[ExportableDocument] = []
        self.reports: list[ProvenanceReport] = []

    def export(self, document: ExportableDocument, filename: str) -> ExportedFile:
        self.documents.append(document)
        return ExportedFile(filename, "application/pdf", b"%PDF-fake")

    def export_provenance(self, report: ProvenanceReport, filename: str) -> ExportedFile:
        self.reports.append(report)
        return ExportedFile(filename, "application/pdf", b"%PDF-fake")


class FailingExporter:
    def export(self, document: ExportableDocument, filename: str) -> ExportedFile:
        raise ExportError(f"pango failure for {CANARY}")

    def export_provenance(self, report: ProvenanceReport, filename: str) -> ExportedFile:
        raise ExportError(f"pango failure for {CANARY}")


@pytest.fixture
def fake(api: Api) -> Iterator[FakeExporter]:
    exporter = FakeExporter()
    api.app.dependency_overrides[get_exporter] = lambda: exporter
    yield exporter
    api.app.dependency_overrides.pop(get_exporter, None)


def _approved(api: Api, plan: str | None = None) -> dict[str, Any]:
    document = _approvable(api)
    if plan is not None:
        document = _edit(api, document, {PLAN: plan}).json()
        document = _action(api, document, "review").json()
    approved = _action(api, document, "approve")
    assert approved.status_code == 200, approved.text
    body: dict[str, Any] = approved.json()
    return body


def _export(api: Api, document: dict[str, Any], kind: str = "export", **headers: Any) -> Any:
    return api.client.post(f"/documents/{document['id']}/{kind}", headers=api.headers(**headers))


def _pages(content: bytes) -> list[str]:
    """Texte de chaque page, espaces normalisés (l'extraction peut couper les lignes)."""
    return [
        " ".join((page.extract_text() or "").split())
        for page in PdfReader(io.BytesIO(content)).pages
    ]


def _audit(api: Api) -> list[AuditEventRow]:
    with api.session() as session:
        return list(session.scalars(select(AuditEventRow)).all())


# F-18 : export après approbation seulement, tracé


def test_F18_export_is_possible_after_approval_only(api: Api, fake: FakeExporter) -> None:
    document = _approvable(api)
    refused = _export(api, document)
    assert refused.status_code == 409
    assert refused.json() == {"detail": "document_not_approved"}
    assert fake.documents == []
    with api.session() as session:
        assert session.scalars(select(Export)).all() == []
    assert not [e for e in _audit(api) if e.action == "exported"]


def test_F18_each_export_is_traced_and_repeatable(api: Api, fake: FakeExporter) -> None:
    document = _approved(api)
    for _ in range(2):
        response = _export(api, document)
        assert response.status_code == 200, response.text
        assert response.headers["content-type"] == "application/pdf"
        assert response.headers["content-disposition"].startswith("attachment;")
        assert response.headers["cache-control"] == "no-store"
    with api.session() as session:
        exports = session.scalars(select(Export)).all()
    assert len(exports) == 2
    assert {(str(e.document_id), e.version, e.format) for e in exports} == {
        (document["id"], document["version"], "pdf")
    }
    current = api.client.get(f"/documents/{document['id']}", headers=api.headers()).json()
    assert current["state"] == "approved" and current["version"] == document["version"]


def test_F18_exported_document_has_no_origin_source_or_draft_marker(
    api: Api, fake: FakeExporter
) -> None:
    document = _approved(api)
    _export(api, document)
    exported = fake.documents[0]
    assert exported.approver_name == "Dr Test"
    assert exported.clinic == DEMO.snapshot()
    sections = dict(exported.sections)
    assert sections[PLAN] == "Exercise stress test requested."
    dumped = repr(exported)
    for marker in ("origin", "sources", "citation", "draft", "status", "consultation_text"):
        assert marker not in dumped


def test_F18_pdf_text_has_no_mention_of_ai_sources_or_draft(api: Api) -> None:
    require_weasyprint()
    document = _approved(api)
    response = _export(api, document)
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
    text = "\n".join(_pages(response.content))
    assert "REFERRAL LETTER" in text.upper()
    assert "Exercise stress test requested." in text
    assert "Approved by Dr Test on 2026-01-01" in text
    assert FORBIDDEN_IN_CLINICAL_PDF.search(text) is None, FORBIDDEN_IN_CLINICAL_PDF.search(text)


# F-24 et P15 : en-tête et pied de page sur chaque page, valeurs figées, pagination


def test_F24_header_and_footer_on_every_page_with_frozen_clinic_and_pagination(
    api: Api,
) -> None:
    require_weasyprint()
    long_plan = "\n".join(f"Step {i}: follow-up instruction line." for i in range(1, 160))
    document = _approved(api, plan=long_plan)
    moved = ClinicProfile("Moved Clinic", "2 Road", "Town", "11111", "1", "a@b.example", "x")
    api.app.dependency_overrides[get_clinic_profile] = lambda: moved
    response = _export(api, document)
    assert response.status_code == 200, response.text
    pages = _pages(response.content)
    assert len(pages) >= 2
    for number, text in enumerate(pages, start=1):
        for value in DEMO.snapshot().values():
            assert text.count(value) >= 2, (number, value)  # en-tête et pied de page
        assert f"{number} / {len(pages)}" in text
        assert "Moved Clinic" not in text


# N-06 : contenu HTML échappé, aucune requête sortante


def test_N06_html_in_a_section_is_escaped_and_rendering_makes_no_request(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    require_weasyprint()
    requests: list[str] = []
    original = pdf_adapter.blocking_url_fetcher
    monkeypatch.setattr(
        pdf_adapter, "blocking_url_fetcher", lambda on_request=None: original(requests.append)
    )
    injected = (
        '<img src="http://attacker.example/x.png">'
        '<link rel="stylesheet" href="file:///etc/passwd"><b>bold</b>'
    )
    document = _approved(api, plan=injected)
    response = _export(api, document)
    assert response.status_code == 200, response.text
    text = "\n".join(_pages(response.content))
    assert '<img src="http://attacker.example/x.png">' in text
    assert "<b>bold</b>" in text
    assert requests == []


def test_N06_pdf_renderer_refuses_every_url() -> None:
    require_weasyprint()
    requests: list[str] = []
    html = (
        '<html><head><link rel="stylesheet" href="file:///etc/passwd"></head>'
        '<body><img src="http://attacker.example/x.png"><p>Body</p></body></html>'
    )
    content = pdf_adapter.render_pdf(html, requests.append)
    assert content.startswith(b"%PDF")
    assert set(requests) == {"file:///etc/passwd", "http://attacker.example/x.png"}


# F-23 / L-08 : rapport de provenance séparé


def test_F23_provenance_report_before_and_after_approval_is_traced(
    api: Api, fake: FakeExporter
) -> None:
    document = _approvable(api)
    before = _export(api, document, "provenance-report")
    assert before.status_code == 200, before.text
    assert before.headers["content-disposition"].startswith('attachment; filename="provenance-')
    approved = _action(api, document, "approve").json()
    after = _export(api, approved, "provenance-report")
    assert after.status_code == 200, after.text
    assert [r.state for r in fake.reports] == ["Under Review", "Approved"]
    report = fake.reports[0]
    rows = {entry.section: entry for entry in report.entries}
    assert rows["Patient and encounter"].origin == "Superbill"
    assert rows[PLAN].origin == "Clinician"
    assert rows[PLAN].sources[0].startswith("Clinician edit by Dr Test on ")
    assert rows["Reason for referral"].origin == "AI"
    assert rows["Reason for referral"].sources[0].startswith("Consultation text, characters 0-")
    traced = [e for e in _audit(api) if e.action == "provenance_report_generated"]
    assert [(str(e.document_id), e.version) for e in traced] == [
        (document["id"], document["version"]),
        (document["id"], document["version"]),
    ]


def test_F23_provenance_report_pdf_is_separate_from_the_clinical_pdf(api: Api) -> None:
    require_weasyprint()
    document = _approved(api)
    report = _export(api, document, "provenance-report")
    assert report.status_code == 200, report.text
    report_text = "\n".join(_pages(report.content))
    assert "Provenance report" in report_text
    assert "Consultation text, characters" in report_text
    assert "not part of the clinical document" in report_text
    clinical = "\n".join(_pages(_export(api, document).content))
    assert "Provenance" not in clinical
    assert "Consultation text, characters" not in clinical


# F-20 : exporté et rapport de provenance généré, tracés


def test_F20_export_and_provenance_report_are_audited_with_actor_document_and_version(
    api: Api, fake: FakeExporter
) -> None:
    document = _approved(api)
    _export(api, document)
    _export(api, document, "provenance-report")
    events = {e.action: e for e in _audit(api)}
    for action in ("exported", "provenance_report_generated"):
        event = events[action]
        assert str(event.document_id) == document["id"]
        assert event.version == document["version"]
        assert event.actor_id is not None and event.occurred_at is not None


# N-11 : échec PDF


def test_N11_pdf_failure_gives_a_safe_message_and_document_stays_approved(
    api: Api, log_dir: Path
) -> None:
    document = _approved(api)
    before = api.client.get(f"/documents/{document['id']}", headers=api.headers()).json()
    api.app.dependency_overrides[get_exporter] = FailingExporter
    for kind in ("export", "provenance-report"):
        response = _export(api, document, kind)
        assert response.status_code == 500
        assert response.json() == {"detail": "export_failed"}
        assert CANARY not in response.text and "pango" not in response.text
    after = api.client.get(f"/documents/{document['id']}", headers=api.headers()).json()
    assert after == before
    assert after["state"] == "approved" and after["version"] == document["version"]
    with api.session() as session:
        assert session.scalars(select(Export)).all() == []
    actions = {e.action for e in _audit(api)}
    assert not actions & {"exported", "provenance_report_generated"}
    logs = "".join(p.read_text(encoding="utf-8") for p in log_dir.glob("*.log*"))
    assert "export_failed" in logs
    assert CANARY not in logs and "pango" not in logs


# F-25 : routes du jalon réservées à l'auteur


def test_F25_export_routes_hide_documents_of_another_clinician(
    api: Api, fake: FakeExporter
) -> None:
    document = _approved(api)
    for kind in ("export", "provenance-report"):
        foreign = _export(api, document, kind, subject="clin-other")
        absent = api.client.post(
            f"/documents/{uuid4()}/{kind}", headers=api.headers(subject="clin-other")
        )
        assert foreign.status_code == 404, kind
        assert foreign.json() == absent.json(), kind
        unauthenticated = api.client.post(f"/documents/{document['id']}/{kind}")
        assert unauthenticated.status_code == 401
    assert fake.documents == [] and fake.reports == []
    assert not {e.action for e in _audit(api)} & {"exported", "provenance_report_generated"}


# F-22 : la suppression efface aussi les exports


def test_F22_deletion_also_removes_exports_and_keeps_the_audit(
    api: Api, fake: FakeExporter
) -> None:
    document = _approved(api)
    _export(api, document)
    response = api.client.delete(
        f"/consultations/{document['consultation_id']}", headers=api.headers()
    )
    assert response.status_code == 204
    with api.session() as session:
        for table in (Export, DocumentVersionEvent, DocumentVersion, Document, Consultation):
            assert session.scalars(select(table)).all() == [], table
    actions = [e.action for e in _audit(api)]
    assert "exported" in actions and "approved" in actions
    assert actions.count("consultation_deleted") == 1


# N-10 : conservation avec dates simulées


def _purge(api: Api) -> int:
    with api.session() as session:
        purged = RetentionService(session, api.clock, get_file_store()).purge_consultations()
        session.commit()
    return purged


def _consultations(api: Api) -> list[Consultation]:
    with api.session() as session:
        return list(session.scalars(select(Consultation)).all())


def test_N10_consultation_is_purged_90_days_after_its_last_approval(
    api: Api, fake: FakeExporter
) -> None:
    document = _approved(api)
    _export(api, document)
    with api.session() as session:
        key = session.scalars(select(Consultation.storage_key)).one()
    assert key is not None
    api.clock.advance(timedelta(days=89))
    assert _purge(api) == 0
    assert len(_consultations(api)) == 1
    api.clock.advance(timedelta(days=2))
    assert _purge(api) == 1
    assert _consultations(api) == []
    with api.session() as session:
        for table in (Export, DocumentVersionEvent, DocumentVersion, Document):
            assert session.scalars(select(table)).all() == [], table
    with pytest.raises(FileNotFoundError):
        get_file_store().read(key)
    purged = [e for e in _audit(api) if e.action == PURGE_ACTION]
    assert len(purged) == 1
    assert purged[0].actor_id == SYSTEM_ACTOR
    assert purged[0].document_id is None and purged[0].version is None
    assert {"approved", "exported"} <= {e.action for e in _audit(api)}


def test_N10_never_approved_consultation_is_purged_90_days_after_its_last_activity(
    api: Api,
) -> None:
    consultation_id = _validated(api)
    api.clock.advance(timedelta(days=30))
    api.client.put(
        f"/consultations/{consultation_id}/text",
        json={"text": "Later activity."},
        headers=api.headers(),
    )
    api.clock.advance(timedelta(days=89))
    assert _purge(api) == 0
    api.clock.advance(timedelta(days=2))
    assert _purge(api) == 1
    assert _consultations(api) == []


def test_N10_recent_consultations_of_every_author_are_kept(api: Api) -> None:
    _validated(api)
    api.clock.advance(timedelta(days=10))
    assert _purge(api) == 0
    assert len(_consultations(api)) == 1


# N-08 : canari


def test_N08_export_and_provenance_do_not_log_patient_data(api: Api, log_dir: Path) -> None:
    require_weasyprint()
    document = _approved(api, plan=f'Plan for {CANARY}. <img src="http://x.example/{CANARY}">')
    assert _export(api, document).status_code == 200
    assert _export(api, document, "provenance-report").status_code == 200
    pdf_adapter.render_pdf(f'<img src="http://x.example/{CANARY}">')
    logs = "".join(p.read_text(encoding="utf-8") for p in log_dir.glob("*.log*"))
    assert CANARY not in logs


def test_N10_purge_scheduler_starts_with_the_application_when_enabled(
    monkeypatch: pytest.MonkeyPatch, log_dir: Path
) -> None:
    started = threading.Event()

    async def fake_loop(settings: Settings, clock: Clock) -> None:
        started.set()

    monkeypatch.setattr(main_module, "retention_loop", fake_loop)
    monkeypatch.setenv("RETENTION_ENABLED", "true")
    get_settings.cache_clear()
    try:
        with TestClient(main_module.create_app()) as client:
            client.get("/health")
            assert started.wait(5)
    finally:
        get_settings.cache_clear()


def test_N10_scheduled_purge_applies_the_policy_with_a_simulated_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, log_dir: Path
) -> None:
    configure_logging(str(log_dir), 30)
    url = f"sqlite:///{(tmp_path / 'retention.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    session_factory.cache_clear()
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    with Session(engine) as session:
        for age in (91, 10):
            moment = start - timedelta(days=age)
            session.add(
                Consultation(
                    author_id=uuid4(),
                    state="validated",
                    file_kind="pdf",
                    file_size=1,
                    created_at=moment,
                    updated_at=moment,
                )
            )
        session.commit()
    try:
        run_retention(get_settings(), FixedClock(start))
        with Session(engine) as session:
            assert len(session.scalars(select(Consultation)).all()) == 1
    finally:
        session_factory.cache_clear()
        get_settings.cache_clear()
        engine.dispose()
    logs = "".join(p.read_text(encoding="utf-8") for p in log_dir.glob("*.log*"))
    assert "retention_purged" in logs
    assert "retention_audit_purge_not_configured" in logs


def test_N10_audit_older_than_one_year_is_purged_with_the_purge_role(
    migrated: dict[str, str], tmp_path: Path
) -> None:
    now = datetime(2027, 1, 1, tzinfo=UTC)
    app_engine = create_engine(migrated["app"])
    purge_engine = create_engine(migrated["purge"])
    try:
        with Session(app_engine) as session:
            for age in (366, 10):
                session.add(
                    AuditEventRow(
                        occurred_at=now - timedelta(days=age), actor_id=uuid4(), action="approved"
                    )
                )
            session.commit()
        with Session(app_engine) as session, Session(purge_engine) as purge_session:
            service = RetentionService(session, FixedClock(now), LocalFileStore(str(tmp_path)))
            assert service.purge_audit(purge_session) == 1
            purge_session.commit()
        with Session(app_engine) as session:
            remaining = session.scalars(select(AuditEventRow)).all()
        assert [e.occurred_at for e in remaining] == [now - timedelta(days=10)]
    finally:
        app_engine.dispose()
        purge_engine.dispose()


def test_F18_application_role_can_only_add_or_erase_exports(migrated: dict[str, str]) -> None:
    engine = create_engine(migrated["owner"])
    try:
        with engine.connect() as conn:
            rights = {
                privilege: conn.execute(
                    sql("SELECT has_table_privilege('xeleron_app', 'export', :p)"),
                    {"p": privilege},
                ).scalar_one()
                for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE")
            }
    finally:
        engine.dispose()
    assert rights == {"SELECT": True, "INSERT": True, "UPDATE": False, "DELETE": True}
