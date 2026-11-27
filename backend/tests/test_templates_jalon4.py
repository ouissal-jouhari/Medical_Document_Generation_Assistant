"""Templates (SRS 5.1 à 5.4) et contrôle d'ancrage : sections attendues, sources, anti-invention."""

from typing import Any

import pytest

from app.adapters.templates import load_templates
from app.services.generation import _check_section
from tests.conftest import Api
from tests.test_generation_jalon4 import _validated, _with_llm

EXPECTED: dict[str, list[tuple[str, str]]] = {
    "clinical_note": [
        ("Subjective", "STANDARD"),
        ("Objective", "STANDARD"),
        ("Assessment", "STANDARD"),
        ("Plan", "STANDARD"),
        ("Medications", "SAFETY"),
        ("Allergies and adverse reactions", "SAFETY"),
    ],
    "referral_letter": [
        ("Recipient", "STANDARD"),
        ("Reason for referral", "REQUIRED"),
        ("Urgency", "STANDARD"),
        ("History and clinical summary", "STANDARD"),
        ("Clinical findings and investigation results", "STANDARD"),
        ("Assessment", "REQUIRED"),
        ("Current treatment and medications", "SAFETY"),
        ("Allergies and adverse reactions", "SAFETY"),
        ("Plan and requested actions", "REQUIRED"),
    ],
    "discharge_summary": [
        ("Admission details", "STANDARD"),
        ("Discharge details", "STANDARD"),
        ("Clinical summary", "REQUIRED"),
        ("Investigation results", "STANDARD"),
        ("Medications at discharge", "SAFETY"),
        ("Allergies and adverse reactions", "SAFETY"),
        ("Plan and requested actions", "STANDARD"),
        ("Information and advice given", "STANDARD"),
    ],
}

TEXT = (
    "Admitted on 2026-11-14 with community-acquired pneumonia. "
    "Fever resolved by day 2. WBC was 14.2 x10^9/L on admission. "
    "No intensive care transfer was required. "
    "Discharged home on 2026-11-18. Follow-up with the primary care physician in one week."
)


@pytest.mark.parametrize("template_id", sorted(EXPECTED))
def test_F10_templates_match_srs_sections_and_levels(template_id: str) -> None:
    templates = load_templates("app/templates")
    actual = [(s.name, s.level) for s in templates[template_id].sections]
    assert actual == EXPECTED[template_id]


@pytest.mark.parametrize("template_id", sorted(EXPECTED))
def test_F10_document_returns_all_template_sections_and_the_common_block(
    api: Api, template_id: str
) -> None:
    llm = _with_llm(api)
    llm.result = {"sections": []}
    consultation_id = _validated(api)
    response = api.client.post(
        f"/consultations/{consultation_id}/documents",
        json={"documentType": template_id},
        headers=api.headers(),
    )
    assert response.status_code == 201
    body = response.json()["sections"]
    assert [(s["name"], s["level"]) for s in body["sections"]] == EXPECTED[template_id]
    block = body["common_block"]
    assert {d["code"] for d in block["diagnoses"]} == {"E11.9", "I10"}
    assert {p["code"] for p in block["procedures"]} == {"99213", "36415"}
    assert block["physician"] and block["date_of_service"]


def test_N19_identifiers_are_in_the_common_block_but_never_in_the_prompt(api: Api) -> None:
    llm = _with_llm(api)
    llm.result = {"sections": []}
    consultation_id = _validated(api)
    response = api.client.post(
        f"/consultations/{consultation_id}/documents",
        json={"documentType": "discharge_summary"},
        headers=api.headers(),
    )
    block = response.json()["sections"]["common_block"]
    assert block["patient_name"] == "Jane Doe"
    for identifier in ("Jane Doe", "1980-04-12", "P-000123"):
        assert identifier not in llm.prompt
    assert "E11.9" in llm.prompt


def test_F10_text_with_information_gives_filled_sections_with_valid_sources(api: Api) -> None:
    llm = _with_llm(api)
    llm.result = {
        "sections": [
            {
                "name": "Admission details",
                "status": "PROVIDED",
                "content": "Admitted on 2026-11-14 with community-acquired pneumonia.",
                "citations": ["Admitted on 2026-11-14 with community-acquired pneumonia."],
            },
            {
                "name": "Clinical summary",
                "status": "PROVIDED",
                "content": "Fever resolved by day 2. No intensive care transfer was required.",
                "citations": [
                    "Fever resolved by day 2.",
                    "No intensive care transfer was required.",
                ],
            },
            {
                "name": "Investigation results",
                "status": "PROVIDED",
                "content": "WBC 14.2 x10^9/L on admission.",
                "citations": ["WBC was 14.2 x10^9/L on admission."],
            },
            {
                "name": "Plan and requested actions",
                "status": "PROVIDED",
                "content": "Follow-up with the primary care physician in one week.",
                "citations": ["Follow-up with the primary care physician in one week."],
            },
        ]
    }
    consultation_id = _validated(api)
    api.client.put(
        f"/consultations/{consultation_id}/text", json={"text": TEXT}, headers=api.headers()
    )
    response = api.client.post(
        f"/consultations/{consultation_id}/documents",
        json={"documentType": "discharge_summary"},
        headers=api.headers(),
    )
    assert response.status_code == 201
    by_name = {s["name"]: s for s in response.json()["sections"]["sections"]}
    for name in (
        "Admission details",
        "Clinical summary",
        "Investigation results",
        "Plan and requested actions",
    ):
        section = by_name[name]
        assert section["status"] == "PROVIDED", name
        assert section["sources"], name
        for source in section["sources"]:
            assert TEXT[source["start"] : source["end"]] == source["citation"]
            assert source["kind"] == "consultation_text"


def test_F11_information_absent_from_the_text_stays_not_provided(api: Api) -> None:
    llm = _with_llm(api)
    llm.result = {
        "sections": [
            {
                "name": "Discharge details",
                "status": "PROVIDED",
                "content": "Discharged home on 2026-11-18.",
                "citations": ["Discharged home on 2026-11-18."],
            },
            {
                "name": "Investigation results",
                "status": "NOT_PROVIDED",
                "content": None,
                "citations": [],
            },
        ]
    }
    consultation_id = _validated(api)
    api.client.put(
        f"/consultations/{consultation_id}/text", json={"text": TEXT}, headers=api.headers()
    )
    response = api.client.post(
        f"/consultations/{consultation_id}/documents",
        json={"documentType": "discharge_summary"},
        headers=api.headers(),
    )
    by_name = {s["name"]: s for s in response.json()["sections"]["sections"]}
    assert by_name["Discharge details"]["status"] == "PROVIDED"
    assert by_name["Investigation results"]["status"] == "NOT_PROVIDED"
    assert by_name["Investigation results"]["content"] is None


def test_S02_medication_and_allergy_never_invented_without_a_source(api: Api) -> None:
    llm = _with_llm(api)
    llm.result = {
        "sections": [
            {
                "name": "Medications at discharge",
                "status": "PROVIDED",
                "content": "Amoxicillin 500 mg three times daily.",
                "citations": [],
            },
            {
                "name": "Allergies and adverse reactions",
                "status": "PROVIDED",
                "content": "Penicillin allergy.",
                "citations": ["Penicillin allergy"],
            },
        ]
    }
    consultation_id = _validated(api)
    api.client.put(
        f"/consultations/{consultation_id}/text", json={"text": TEXT}, headers=api.headers()
    )
    response = api.client.post(
        f"/consultations/{consultation_id}/documents",
        json={"documentType": "discharge_summary"},
        headers=api.headers(),
    )
    by_name = {s["name"]: s for s in response.json()["sections"]["sections"]}
    for name in ("Medications at discharge", "Allergies and adverse reactions"):
        assert by_name[name]["status"] == "NOT_PROVIDED"
        assert by_name[name]["content"] is None
        assert by_name[name]["sources"] == []


def _entry(content: str, *citations: str) -> dict[str, Any]:
    return {"name": "X", "status": "PROVIDED", "content": content, "citations": list(citations)}


def test_F10_lowercase_unit_is_not_mistaken_for_an_icd_code() -> None:
    """Cause d'un rejet : « x10^9/L » était lu comme le code X10."""
    text = "WBC was 14.2 x10^9/L on admission."
    sources, reason = _check_section(_entry("WBC 14.2 x10^9/L.", text), text, text, set())
    assert reason is None
    assert sources[0]["start"] == 0


def test_S02_sourced_negation_is_accepted_but_unsourced_negation_is_rejected() -> None:
    text = "No intensive care transfer was required. Cough for two days."
    sources, reason = _check_section(
        _entry("No ICU transfer.", "No intensive care transfer was required."), text, text, set()
    )
    assert reason is None and sources
    _, reason = _check_section(_entry("No allergies.", "Cough for two days."), text, text, set())
    assert reason == "unsupported_negation"


def test_S02_code_absent_from_superbill_and_text_is_rejected() -> None:
    text = "Cough for two days."
    _, reason = _check_section(_entry("Pneumonia J18.9.", text), text, text, {"I10"})
    assert reason == "code_not_in_sources"
    _, reason = _check_section(_entry("Pneumonia J18.9.", text), text, text, {"J18.9"})
    assert reason is None


def test_F10_coded_lines_are_valid_superbill_sources() -> None:
    text = "Cough."
    sources_text = text + "\nE11.9: Type 2 diabetes mellitus without complications"
    sources, reason = _check_section(
        _entry("Type 2 diabetes (E11.9).", "E11.9: Type 2 diabetes mellitus without complications"),
        text,
        sources_text,
        {"E11.9"},
    )
    assert reason is None
    assert sources[0]["kind"] == "superbill"
