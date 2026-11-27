"""Tests automatiques des exigences du jalon 5 : revue, versions et approbation."""

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.adapters.models import AuditEventRow, DocumentVersion
from app.adapters.templates import load_templates
from app.api.deps import get_clinic_profile
from app.core.config import get_settings
from app.domain.clinic import ClinicProfile
from app.domain.document import (
    DocumentState,
    ReviewSnapshot,
    approval_blockers,
    ensure_modifiable,
)
from app.domain.errors import DocumentApproved, VersionConflict
from app.services.generation import GenerationService
from app.services.review import ReviewService
from tests.conftest import CANARY, Api
from tests.helpers_routes import api_routes
from tests.test_generation_jalon4 import FakeLlm, _validated, _with_llm

TEXT = (
    "Referred to cardiology for chest pain on exertion. "
    "Assessment: stable angina suspected. "
    "Taking aspirin 75 mg daily."
)
REASON = "Reason for referral"
ASSESSMENT = "Assessment"
PLAN = "Plan and requested actions"
MEDICATIONS = "Current treatment and medications"
ALLERGIES = "Allergies and adverse reactions"


def _section(name: str, content: str | None = None) -> dict[str, Any]:
    if content is None:
        return {"name": name, "status": "NOT_PROVIDED", "content": None, "citations": []}
    return {"name": name, "status": "PROVIDED", "content": content, "citations": [content]}


def _referral_result() -> dict[str, Any]:
    return {
        "sections": [
            _section(REASON, "Referred to cardiology for chest pain on exertion."),
            _section(ASSESSMENT, "Assessment: stable angina suspected."),
            _section(MEDICATIONS, "Taking aspirin 75 mg daily."),
            _section(PLAN),
            _section(ALLERGIES),
        ]
    }


def _referral(api: Api, text: str | None = TEXT) -> tuple[FakeLlm, str, dict[str, Any]]:
    llm = _with_llm(api)
    llm.result = _referral_result()
    consultation_id = _validated(api)
    if text is not None:
        api.client.put(
            f"/consultations/{consultation_id}/text", json={"text": text}, headers=api.headers()
        )
    created = api.client.post(
        f"/consultations/{consultation_id}/documents",
        json={"documentType": "referral_letter"},
        headers=api.headers(),
    )
    assert created.status_code == 201, created.text
    return llm, consultation_id, created.json()


def _sections(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["name"]: s for s in document["sections"]["sections"]}


def _edit(api: Api, document: dict[str, Any], edits: dict[str, str | None]) -> Any:
    return api.client.put(
        f"/documents/{document['id']}/sections",
        json={
            "expectedVersion": document["version"],
            "sections": [{"name": n, "content": c} for n, c in edits.items()],
        },
        headers=api.headers(),
    )


def _action(api: Api, document: dict[str, Any], action: str, **extra: Any) -> Any:
    return api.client.post(
        f"/documents/{document['id']}/{action}",
        json={"expectedVersion": document["version"], **extra},
        headers=api.headers(),
    )


def _approvable(api: Api) -> dict[str, Any]:
    """Document dont la version courante est complète et relue."""
    _, _, document = _referral(api)
    edited = _edit(api, document, {PLAN: "Exercise stress test requested."}).json()
    reviewed = _action(api, edited, "review")
    assert reviewed.status_code == 200, reviewed.text
    body: dict[str, Any] = reviewed.json()
    return body


# F-13 / S-01 / S-05 : écran de revue


def test_F13_review_exposes_draft_banner_origins_statuses_and_missing_information(
    api: Api,
) -> None:
    _, _, document = _referral(api)
    assert document["state"] == "under_review"
    assert document["draft"] is True
    sections = _sections(document)
    assert sections[REASON]["status"] == "PROVIDED"
    assert sections[REASON]["origin"] == "ai"
    assert sections[REASON]["sources"][0]["kind"] == "consultation_text"
    assert sections[PLAN]["status"] == "NOT_PROVIDED"
    assert {s["level"] for s in sections.values()} >= {"REQUIRED", "SAFETY"}
    missing = {(m["name"], m["level"]) for m in document["missing_information"]}
    expected = {(n, s["level"]) for n, s in sections.items() if s["status"] == "NOT_PROVIDED"}
    assert missing == expected
    assert {(PLAN, "REQUIRED"), (ALLERGIES, "SAFETY")} <= missing
    # Superbill : bloc commun ; clinicien : après édition.
    assert document["sections"]["common_block"]["diagnoses"]
    edited = _edit(api, document, {PLAN: "Exercise stress test requested."}).json()
    assert _sections(edited)[PLAN]["origin"] == "clinician"
    assert _sections(edited)[PLAN]["sources"][0]["kind"] == "clinician"


def test_F13_safety_sections_missing_are_listed(api: Api) -> None:
    _, _, document = _referral(api)
    safety = [m["name"] for m in document["missing_information"] if m["level"] == "SAFETY"]
    assert safety == [ALLERGIES]


def test_S01_banner_disappears_only_after_approval(api: Api) -> None:
    document = _approvable(api)
    assert document["draft"] is True
    approved = _action(api, document, "approve").json()
    assert approved["draft"] is False


# F-14 : édition et versions


def test_F14_edit_creates_edited_version_and_previous_stays_intact(api: Api) -> None:
    _, _, document = _referral(api)
    response = _edit(api, document, {ASSESSMENT: "Stable angina, confirmed by clinician."})
    assert response.status_code == 200
    edited = response.json()
    assert (edited["version"], edited["version_kind"]) == (2, "edited")
    assert edited["version_author_id"] is not None
    assert edited["version_created_at"].startswith("2026-01-01")
    history = api.client.get(f"/documents/{document['id']}/versions", headers=api.headers()).json()
    assert [v["number"] for v in history] == [2, 1]
    first = {s["name"]: s for s in history[1]["sections"]["sections"]}
    assert first[ASSESSMENT]["content"] == "Assessment: stable angina suspected."
    assert history[1]["kind"] == "ai_generated"


def test_F14_one_save_creates_one_version_for_several_sections(api: Api) -> None:
    _, _, document = _referral(api)
    edited = _edit(api, document, {PLAN: "Stress test.", ALLERGIES: "Penicillin (rash)."}).json()
    assert edited["version"] == 2
    unchanged = _edit(api, edited, {PLAN: "Stress test."}).json()
    assert unchanged["version"] == 2


def test_F14_concurrent_edit_with_stale_version_is_refused(api: Api) -> None:
    _, _, document = _referral(api)
    assert _edit(api, document, {PLAN: "First edit."}).status_code == 200
    stale = _edit(api, document, {PLAN: "Concurrent edit."})
    assert stale.status_code == 409
    assert stale.json() == {"detail": "version_conflict"}
    current = api.client.get(f"/documents/{document['id']}", headers=api.headers()).json()
    assert _sections(current)[PLAN]["content"] == "First edit."


def test_F14_database_refuses_two_versions_with_the_same_number(api: Api) -> None:
    _, _, document = _referral(api)
    with api.session() as session:
        first = session.scalars(select(DocumentVersion)).one()
        session.add(
            DocumentVersion(
                document_id=first.document_id,
                number=1,
                kind="edited",
                author_id=first.author_id,
                created_at=first.created_at,
                content={},
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_F14_unknown_section_is_refused(api: Api) -> None:
    _, _, document = _referral(api)
    response = _edit(api, document, {"Patient name": "x"})
    assert response.status_code == 422
    assert response.json()["detail"] == "validation_failed"


# F-15 : rejet et régénération


def test_F15_rejected_version_is_kept_and_regeneration_creates_ai_version(api: Api) -> None:
    llm, _, document = _referral(api)
    rejected = _action(api, document, "reject")
    assert rejected.status_code == 200
    assert rejected.json()["rejected"] is not None
    llm.result = {"sections": [_section(PLAN, "Taking aspirin 75 mg daily.")]}
    regenerated = _action(api, rejected.json(), "regenerate")
    assert regenerated.status_code == 200, regenerated.text
    body = regenerated.json()
    assert (body["version"], body["version_kind"], body["rejected"]) == (2, "ai_generated", None)
    history = api.client.get(f"/documents/{document['id']}/versions", headers=api.headers()).json()
    assert history[1]["rejected"] is not None
    assert history[1]["sections"] == document["sections"]


def test_F15_regeneration_requires_a_rejected_version(api: Api) -> None:
    _, _, document = _referral(api)
    response = _action(api, document, "regenerate")
    assert response.status_code == 409
    assert response.json() == {"detail": "wrong_state"}


def test_N11_failed_regeneration_keeps_current_version_intact(api: Api) -> None:
    llm, _, document = _referral(api)
    rejected = _action(api, document, "reject").json()
    llm.error = TimeoutError(CANARY)
    response = _action(api, rejected, "regenerate")
    assert response.status_code == 504
    assert response.json() == {"detail": "llm_timeout"}
    assert CANARY not in response.text
    current = api.client.get(f"/documents/{document['id']}", headers=api.headers()).json()
    assert current["version"] == 1
    assert current["sections"] == document["sections"]
    assert current["state"] == "under_review"


# F-16 : rollback et historique


def test_F16_rollback_restores_old_content_in_new_version_and_history_stays_intact(
    api: Api,
) -> None:
    _, _, document = _referral(api)
    edited = _edit(api, document, {ASSESSMENT: "Changed assessment."}).json()
    restored = _action(api, edited, "rollback", toVersion=1)
    assert restored.status_code == 200, restored.text
    body = restored.json()
    assert (body["version"], body["restored_from"]) == (3, 1)
    assert body["sections"] == document["sections"]
    history = api.client.get(f"/documents/{document['id']}/versions", headers=api.headers()).json()
    assert [v["number"] for v in history] == [3, 2, 1]
    assert {s["name"]: s for s in history[1]["sections"]["sections"]}[ASSESSMENT][
        "content"
    ] == "Changed assessment."


def test_F16_rollback_to_current_or_unknown_version_is_refused(api: Api) -> None:
    _, _, document = _referral(api)
    assert _action(api, document, "rollback", toVersion=1).status_code == 409
    assert _action(api, document, "rollback", toVersion=7).status_code == 409


def test_F16_version_history_is_viewable_with_marks(api: Api) -> None:
    document = _approvable(api)
    approved = _action(api, document, "approve").json()
    history = api.client.get(f"/documents/{approved['id']}/versions", headers=api.headers())
    assert history.status_code == 200
    latest = history.json()[0]
    assert latest["reviewed"] is not None
    assert latest["approved"] is True
    assert history.json()[1]["approved"] is False


# F-26 : marquer comme relu


def test_F26_mark_reviewed_records_author_version_and_date(api: Api) -> None:
    _, _, document = _referral(api)
    reviewed = _action(api, document, "review").json()
    assert reviewed["reviewed"]["occurred_at"].startswith("2026-01-01")
    assert reviewed["reviewed"]["actor_id"] == reviewed["version_author_id"]
    with api.session() as session:
        event = session.scalars(
            select(AuditEventRow).where(AuditEventRow.action == "reviewed")
        ).one()
    assert (str(event.document_id), event.version) == (document["id"], 1)


def test_F26_new_version_cancels_reviewed_and_approval_requires_current_reviewed(
    api: Api,
) -> None:
    document = _approvable(api)
    edited = _edit(api, document, {ALLERGIES: "Penicillin (rash)."}).json()
    assert edited["reviewed"] is None
    refused = _action(api, edited, "approve")
    assert refused.status_code == 409
    assert refused.json() == {"detail": "approval_blocked", "missing": ["not_reviewed"]}


def test_F26_rejected_version_cannot_be_reviewed_or_approved(api: Api) -> None:
    document = _approvable(api)
    rejected = _action(api, document, "reject").json()
    assert _action(api, rejected, "review").status_code == 409
    refused = _action(api, rejected, "approve")
    assert refused.status_code == 409
    assert "version_rejected" in refused.json()["missing"]


# F-17 : approbation


def test_F17_approval_blocked_when_required_section_not_provided(api: Api) -> None:
    _, _, document = _referral(api)
    reviewed = _action(api, document, "review").json()
    refused = _action(api, reviewed, "approve")
    assert refused.status_code == 409
    assert refused.json() == {"detail": "approval_blocked", "missing": [PLAN]}
    current = api.client.get(f"/documents/{document['id']}", headers=api.headers()).json()
    assert current["state"] == "under_review"


def test_F17_editing_a_not_provided_section_makes_it_provided(api: Api) -> None:
    _, _, document = _referral(api)
    edited = _edit(api, document, {PLAN: "Exercise stress test requested."}).json()
    assert _sections(edited)[PLAN]["status"] == "PROVIDED"
    emptied = _edit(api, edited, {PLAN: "   "}).json()
    assert _sections(emptied)[PLAN]["status"] == "NOT_PROVIDED"


def test_F17_approval_records_author_and_date_and_freezes_the_document(api: Api) -> None:
    document = _approvable(api)
    approved = _action(api, document, "approve")
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["state"] == "approved"
    assert body["approver_name"] == "Dr Test"
    assert body["approved_at"].startswith("2026-01-01")
    assert body["approved_version"] == body["version"]
    for action, extra in (
        ("review", {}),
        ("reject", {}),
        ("regenerate", {}),
        ("approve", {}),
        ("rollback", {"toVersion": 1}),
    ):
        response = _action(api, body, action, **extra)
        assert response.status_code == 409, action
        assert response.json() == {"detail": "document_approved"}, action
    before = api.client.get(f"/documents/{body['id']}", headers=api.headers()).json()
    edit = _edit(api, body, {PLAN: "Changed after approval."})
    assert edit.json() == {"detail": "document_approved"}
    after = api.client.get(f"/documents/{body['id']}", headers=api.headers()).json()
    assert after == before


def test_F17_freeze_is_enforced_by_the_domain() -> None:
    approved = ReviewSnapshot(DocumentState.APPROVED, 2, True, False)
    with pytest.raises(DocumentApproved):
        ensure_modifiable(approved, 2)
    under_review = ReviewSnapshot(DocumentState.UNDER_REVIEW, 2, True, False)
    with pytest.raises(VersionConflict):
        ensure_modifiable(under_review, 1)


@pytest.mark.parametrize(
    ("document_type", "required"),
    [
        ("referral_letter", [REASON, ASSESSMENT, PLAN]),
        ("discharge_summary", ["Clinical summary"]),
    ],
)
def test_F17_referral_and_discharge_without_text_cannot_be_approved(
    api: Api, document_type: str, required: list[str]
) -> None:
    llm = _with_llm(api)
    llm.result = {"sections": []}
    consultation_id = _validated(api)
    created = api.client.post(
        f"/consultations/{consultation_id}/documents",
        json={"documentType": document_type},
        headers=api.headers(),
    ).json()
    assert created["text_snapshot"] is None
    reviewed = _action(api, created, "review").json()
    refused = _action(api, reviewed, "approve")
    assert refused.status_code == 409
    assert refused.json()["missing"] == required


def test_S06_generation_never_approves_automatically(api: Api) -> None:
    llm = _with_llm(api)
    llm.result = {"sections": []}
    consultation_id = _validated(api)
    created = api.client.post(
        f"/consultations/{consultation_id}/documents",
        json={"documentType": "clinical_note"},
        headers=api.headers(),
    ).json()
    assert created["state"] == "under_review"
    assert approval_blockers(
        ReviewSnapshot(DocumentState.UNDER_REVIEW, 1, False, False), created["sections"]
    ) == ["not_reviewed"]


# F-19 : nouveau document après approbation


def test_F19_create_new_document_regenerates_same_type_and_old_stays_unchanged(
    api: Api,
) -> None:
    document = _approvable(api)
    _action(api, document, "approve")
    approved = api.client.get(f"/documents/{document['id']}", headers=api.headers()).json()
    created = api.client.post(f"/documents/{approved['id']}/new-document", headers=api.headers())
    assert created.status_code == 201, created.text
    new = created.json()
    assert new["id"] != approved["id"]
    assert (new["document_type"], new["state"], new["version"]) == (
        "referral_letter",
        "under_review",
        1,
    )
    assert new["version_kind"] == "ai_generated"
    old = api.client.get(f"/documents/{approved['id']}", headers=api.headers()).json()
    assert old == approved


def test_F19_create_new_document_requires_an_approved_document(api: Api) -> None:
    _, _, document = _referral(api)
    response = api.client.post(f"/documents/{document['id']}/new-document", headers=api.headers())
    assert response.status_code == 409


# F-20 : audit des actions de revue


def test_F20_review_actions_are_audited_with_actor_document_and_version(api: Api) -> None:
    llm, _, document = _referral(api)
    rejected = _action(api, document, "reject").json()
    regenerated = _action(api, rejected, "regenerate").json()
    edited = _edit(api, regenerated, {PLAN: "Exercise stress test requested."}).json()
    edited_again = _edit(api, edited, {PLAN: "Echocardiogram requested."}).json()
    restored = _action(api, edited_again, "rollback", toVersion=3).json()
    reviewed = _action(api, restored, "review").json()
    approved = _action(api, reviewed, "approve").json()
    assert approved["state"] == "approved"
    with api.session() as session:
        events = session.scalars(select(AuditEventRow).order_by(AuditEventRow.version)).all()
    actions = [(e.action, e.version) for e in events]
    assert actions == [
        ("generated", 1),
        ("rejected", 1),
        ("generated", 2),
        ("rollback", 5),
        ("reviewed", 5),
        ("approved", 5),
    ]
    assert {str(e.document_id) for e in events} == {document["id"]}
    assert len({e.actor_id for e in events}) == 1
    assert all(e.occurred_at is not None for e in events)


# H-01 / H-02 / F-24 : coordonnées de la clinique


def test_H02_clinic_details_are_frozen_at_approval(api: Api) -> None:
    document = _approvable(api)
    approved = _action(api, document, "approve").json()
    assert approved["clinic"]["name"] == "XeleronIA Demo Clinic"
    assert set(approved["clinic"]) == {
        "name",
        "address",
        "city",
        "postal_code",
        "phone",
        "email",
        "website",
    }
    moved = ClinicProfile("Moved Clinic", "2 Road", "Town", "11111", "1", "a@b.example", "x")
    api.app.dependency_overrides[get_clinic_profile] = lambda: moved
    after = api.client.get(f"/documents/{approved['id']}", headers=api.headers()).json()
    assert after["clinic"]["name"] == "XeleronIA Demo Clinic"


def test_H01_no_route_modifies_clinic_details(api: Api) -> None:
    for route, _ in api_routes(api.app):
        assert "clinic" not in route.path.lower(), route.path


def test_H02_clinic_details_absent_before_approval(api: Api) -> None:
    _, _, document = _referral(api)
    assert document["clinic"] is None


# F-25 : routes du jalon réservées à l'auteur


def test_F25_review_routes_hide_documents_of_another_clinician(api: Api) -> None:
    _, _, created = _referral(api)
    document = api.client.get(f"/documents/{created['id']}", headers=api.headers()).json()
    other = api.headers(subject="clin-other")
    calls: list[tuple[str, str, dict[str, Any] | None]] = [
        ("GET", "", None),
        ("GET", "/versions", None),
        ("PUT", "/sections", {"expectedVersion": 1, "sections": [{"name": PLAN}]}),
        ("POST", "/reject", {"expectedVersion": 1}),
        ("POST", "/regenerate", {"expectedVersion": 1}),
        ("POST", "/rollback", {"expectedVersion": 1, "toVersion": 1}),
        ("POST", "/review", {"expectedVersion": 1}),
        ("POST", "/approve", {"expectedVersion": 1}),
        ("POST", "/new-document", None),
    ]
    for method, suffix, body in calls:
        foreign = api.client.request(
            method, f"/documents/{document['id']}{suffix}", json=body, headers=other
        )
        absent = api.client.request(
            method, f"/documents/{uuid4()}{suffix}", json=body, headers=other
        )
        assert foreign.status_code == 404, suffix
        assert foreign.json() == absent.json(), suffix
    current = api.client.get(f"/documents/{document['id']}", headers=api.headers()).json()
    assert current == document


def test_F25_every_document_route_is_covered(api: Api) -> None:
    paths = {r.path for r, _ in api_routes(api.app) if r.path.startswith("/documents")}
    assert paths == {
        "/documents/{document_id}",
        "/documents/{document_id}/versions",
        "/documents/{document_id}/sections",
        "/documents/{document_id}/reject",
        "/documents/{document_id}/regenerate",
        "/documents/{document_id}/rollback",
        "/documents/{document_id}/review",
        "/documents/{document_id}/approve",
        "/documents/{document_id}/new-document",
    }


# N-08 : canari


def test_N08_review_actions_do_not_log_patient_data(api: Api, log_dir: Path) -> None:
    _, _, document = _referral(api)
    edited = _edit(api, document, {PLAN: f"Plan for {CANARY}."}).json()
    _action(api, edited, "approve")
    _action(api, edited, "review")
    logs = "\n".join(p.read_text(encoding="utf-8") for p in log_dir.glob("xeleron.log*"))
    assert CANARY not in logs


# F-14 : immuabilité garantie par la base (rôle applicatif)


def test_F14_application_role_cannot_update_versions_or_review_marks(
    migrated: dict[str, str],
) -> None:
    engine = sa.create_engine(migrated["app"])
    for table in ("document_version", "document_version_event"):
        with engine.connect() as conn, pytest.raises(ProgrammingError) as error:
            conn.execute(sa.text(f"UPDATE {table} SET id = id"))  # noqa: S608 - nom fixe
        assert "permission denied" in str(error.value)
    with engine.connect() as conn:
        conn.execute(sa.text("SELECT count(*) FROM document_version"))
    engine.dispose()


def test_F14_race_between_two_saves_is_refused_by_optimistic_lock(api: Api) -> None:
    """Deux enregistrements lisent la version 1 ; le second à écrire est refusé."""
    _, _, document = _referral(api)
    templates = load_templates(get_settings().template_dir)
    profile = get_clinic_profile()
    first, second = api.session(), api.session()

    def service(session: Session) -> ReviewService:
        return ReviewService(
            session, api.clock, GenerationService(session, api.clock, FakeLlm(), templates), profile
        )

    author = UUID(document["version_author_id"])
    document_id = UUID(document["id"])
    service(second).view(author, document_id)  # lecture de la version 1
    service(first).edit(author, document_id, 1, {PLAN: "First save."})
    first.commit()
    with pytest.raises(VersionConflict):
        service(second).edit(author, document_id, 1, {PLAN: "Second save."})
    second.rollback()
    first.close()
    second.close()
