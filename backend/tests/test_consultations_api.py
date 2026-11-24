"""F-03, F-05, F-06, F-25 (rejoué), N-11 : flux Uploaded -> Parsed -> Validated par l'API."""

from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from app.domain.errors import ExtractionError
from tests.conftest import CANARY, Api
from tests.superbill_samples import (
    CLEAN_TEXT,
    EXPECTED_CLEAN,
    blank_pdf,
    encrypted_pdf,
    pdf_with_text,
)

PDF = ("superbill.pdf", "application/pdf")


def _upload(
    api: Api, content: bytes, *, name: str = "superbill.pdf", subject: str = "user-a"
) -> Any:
    return api.client.post(
        "/consultations", files={"file": (name, content)}, headers=api.headers(subject=subject)
    )


def _logs(log_dir: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in log_dir.glob("xeleron.log*"))


def _parsed(api: Api, subject: str = "user-a") -> str:
    api.ocr.text = CLEAN_TEXT
    response = _upload(api, pdf_with_text(CLEAN_TEXT), subject=subject)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


# -- F-03 : dépôt et limites ---------------------------------------------------------------


def test_F03_valid_pdf_creates_a_consultation_parsed(api: Api) -> None:
    api.ocr.text = CLEAN_TEXT
    response = _upload(api, pdf_with_text(CLEAN_TEXT))
    assert response.status_code == 201
    body = response.json()
    assert (body["state"], body["extraction"]) == ("parsed", "parsed")
    assert body["data"] == EXPECTED_CLEAN


@pytest.mark.parametrize(
    ("content", "name", "status", "code"),
    [
        (b"texte renomme", "x.pdf", 415, "unsupported_format"),
        (pdf_with_text(CLEAN_TEXT), "x.docx", 415, "unsupported_format"),
        (blank_pdf(4), "x.pdf", 422, "too_many_pages"),
        (encrypted_pdf(), "x.pdf", 422, "encrypted_pdf"),
        (b"%PDF-1.7 casse", "x.pdf", 422, "corrupt_file"),
    ],
)
def test_F03_refused_file_creates_no_consultation(
    api: Api, content: bytes, name: str, status: int, code: str
) -> None:
    response = _upload(api, content, name=name)
    assert response.status_code == status
    assert response.json() == {"detail": code}
    assert api.client.get("/consultations", headers=api.headers()).json() == []


def test_F03_file_over_the_api_limit_is_refused(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("MAX_UPLOAD_BYTES", "1000")
    get_settings.cache_clear()
    response = _upload(api, pdf_with_text(CLEAN_TEXT))
    assert response.status_code == 413
    assert response.json() == {"detail": "file_too_large"}
    assert api.client.get("/consultations", headers=api.headers()).json() == []


def test_F03_upload_requires_authentication(api: Api) -> None:
    response = api.client.post("/consultations", files={"file": ("a.pdf", b"x")})
    assert response.status_code == 401


def test_N08_original_file_name_is_never_stored_or_logged(api: Api, log_dir: Path) -> None:
    api.ocr.text = CLEAN_TEXT
    response = _upload(api, pdf_with_text(CLEAN_TEXT), name=f"{CANARY}.pdf")
    assert response.status_code == 201
    assert CANARY not in response.text
    assert CANARY not in _logs(log_dir)
    stored = list((log_dir.parent / "storage" / "superbills").iterdir())
    assert len(stored) == 1 and CANARY not in stored[0].name


# -- F-06 : échec d'extraction -------------------------------------------------------------


def test_F06_extraction_failure_keeps_uploaded_and_counts_the_failure(api: Api) -> None:
    api.ocr.error = ExtractionError()
    response = _upload(api, pdf_with_text(CLEAN_TEXT))
    assert response.status_code == 201
    body = response.json()
    assert (body["state"], body["extraction"], body["extraction_failures"]) == (
        "uploaded",
        "failed",
        1,
    )
    assert body["data"] is None


def test_F06_text_without_any_field_is_a_failed_extraction(api: Api) -> None:
    api.ocr.text = "Rien d'exploitable ici."
    body = _upload(api, blank_pdf(1)).json()
    assert (body["state"], body["extraction"]) == ("uploaded", "failed")


def test_F06_new_deposit_is_possible_and_failures_are_counted(api: Api) -> None:
    api.ocr.error = ExtractionError()
    consultation_id = _upload(api, blank_pdf(1)).json()["id"]
    again = api.client.post(
        f"/consultations/{consultation_id}/superbill",
        files={"file": ("b.pdf", blank_pdf(1))},
        headers=api.headers(),
    ).json()
    assert (again["state"], again["extraction_failures"]) == ("uploaded", 2)
    api.ocr.error = None
    api.ocr.text = CLEAN_TEXT
    ok = api.client.post(
        f"/consultations/{consultation_id}/superbill",
        files={"file": ("c.pdf", pdf_with_text(CLEAN_TEXT))},
        headers=api.headers(),
    ).json()
    assert (ok["state"], ok["extraction_failures"], ok["extraction"]) == ("parsed", 2, "parsed")


def test_F06_redeposit_replaces_the_stored_file(api: Api, log_dir: Path) -> None:
    api.ocr.error = ExtractionError()
    consultation_id = _upload(api, blank_pdf(1)).json()["id"]
    api.client.post(
        f"/consultations/{consultation_id}/superbill",
        files={"file": ("b.pdf", blank_pdf(2))},
        headers=api.headers(),
    )
    assert len(list((log_dir.parent / "storage" / "superbills").iterdir())) == 1


def test_F06_redeposit_is_refused_once_parsed(api: Api) -> None:
    consultation_id = _parsed(api)
    response = api.client.post(
        f"/consultations/{consultation_id}/superbill",
        files={"file": ("b.pdf", pdf_with_text(CLEAN_TEXT))},
        headers=api.headers(),
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "wrong_state"}


def test_N11_extraction_failure_message_is_safe_and_leaks_nothing(api: Api, log_dir: Path) -> None:
    api.ocr.error = RuntimeError(f"échec sur {CANARY}")
    response = _upload(api, pdf_with_text(CLEAN_TEXT))
    assert response.status_code == 201
    assert CANARY not in response.text
    assert "Traceback" not in response.text
    assert CANARY not in _logs(log_dir)


# -- F-05 : correction et validation explicite ---------------------------------------------


def _edit(data: dict[str, Any]) -> dict[str, Any]:
    body = deepcopy(data)
    body.pop("extraction", None)
    return body


def test_F05_every_field_is_editable_and_each_change_keeps_author_and_date(api: Api) -> None:
    consultation_id = _parsed(api)
    body = _edit(EXPECTED_CLEAN)
    body["patient"]["fullName"] = "Jane Roe"
    body["diagnoses"][0]["code"] = "e11.65"
    response = api.client.put(
        f"/consultations/{consultation_id}/data", json=body, headers=api.headers()
    )
    assert response.status_code == 200, response.text
    out = response.json()
    assert out["data"]["patient"]["fullName"] == "Jane Roe"
    assert out["data"]["diagnoses"][0]["code"] == "E11.65"  # normalisé en majuscules
    assert out["data"]["extraction"] == {"pageCount": 1}
    fields = {c["field"] for c in out["corrections"]}
    assert fields == {"patient.fullName", "diagnoses[0].code"}
    me = api.client.get("/me", headers=api.headers()).json()["id"]
    assert all(c["author_id"] == me and c["changed_at"] for c in out["corrections"])


def test_F05_unchanged_save_records_no_correction(api: Api) -> None:
    consultation_id = _parsed(api)
    out = api.client.put(
        f"/consultations/{consultation_id}/data",
        json=_edit(EXPECTED_CLEAN),
        headers=api.headers(),
    ).json()
    assert out["corrections"] == []


def test_F05_state_changes_to_validated_only_after_explicit_validation(api: Api) -> None:
    consultation_id = _parsed(api)
    assert (
        api.client.get(f"/consultations/{consultation_id}", headers=api.headers()).json()["state"]
        == "parsed"
    )
    api.client.put(
        f"/consultations/{consultation_id}/data",
        json=_edit(EXPECTED_CLEAN),
        headers=api.headers(),
    )
    assert (
        api.client.get(f"/consultations/{consultation_id}", headers=api.headers()).json()["state"]
        == "parsed"
    )
    validated = api.client.post(f"/consultations/{consultation_id}/validate", headers=api.headers())
    assert validated.status_code == 200
    assert validated.json()["state"] == "validated"


def test_F05_validation_is_blocked_by_invalid_data_without_echoing_values(api: Api) -> None:
    consultation_id = _parsed(api)
    body = _edit(EXPECTED_CLEAN)
    body["diagnoses"][0]["code"] = "I1O.9"
    body["diagnoses"][0]["description"] = CANARY
    body["patient"]["dateOfBirth"] = "12/04/1980"
    api.client.put(f"/consultations/{consultation_id}/data", json=body, headers=api.headers())
    response = api.client.post(f"/consultations/{consultation_id}/validate", headers=api.headers())
    assert response.status_code == 422
    result = response.json()
    assert result["detail"] == "validation_failed"
    pairs = {(i["field"], i["code"]) for i in result["issues"]}
    assert ("patient.dateOfBirth", "invalid_date") in pairs
    assert ("diagnoses[0].code", "invalid_icd10cm_format") in pairs
    assert CANARY not in response.text
    assert "12/04/1980" not in response.text and "I1O.9" not in response.text
    state = api.client.get(f"/consultations/{consultation_id}", headers=api.headers()).json()
    assert state["state"] == "parsed"


def test_F05_unknown_icd_code_warns_but_does_not_block_validation(api: Api) -> None:
    consultation_id = _parsed(api)
    body = _edit(EXPECTED_CLEAN)
    body["diagnoses"][0]["code"] = "Z99.99"
    out = api.client.put(
        f"/consultations/{consultation_id}/data", json=body, headers=api.headers()
    ).json()
    assert {"field": "diagnoses[0].code", "code": "icd10cm_unknown", "blocking": False} in out[
        "issues"
    ]
    assert (
        api.client.post(
            f"/consultations/{consultation_id}/validate", headers=api.headers()
        ).status_code
        == 200
    )


def test_F05_validated_data_is_locked(api: Api) -> None:
    consultation_id = _parsed(api)
    api.client.post(f"/consultations/{consultation_id}/validate", headers=api.headers())
    edit = api.client.put(
        f"/consultations/{consultation_id}/data",
        json=_edit(EXPECTED_CLEAN),
        headers=api.headers(),
    )
    assert (edit.status_code, edit.json()) == (409, {"detail": "wrong_state"})
    again = api.client.post(f"/consultations/{consultation_id}/validate", headers=api.headers())
    assert again.status_code == 409


def test_F05_uploaded_consultation_cannot_be_edited_or_validated(api: Api) -> None:
    api.ocr.error = ExtractionError()
    consultation_id = _upload(api, blank_pdf(1)).json()["id"]
    put = api.client.put(f"/consultations/{consultation_id}/data", json={}, headers=api.headers())
    assert put.status_code == 409
    assert (
        api.client.post(
            f"/consultations/{consultation_id}/validate", headers=api.headers()
        ).status_code
        == 409
    )


def test_F05_malformed_payload_is_a_generic_validation_error(api: Api) -> None:
    consultation_id = _parsed(api)
    response = api.client.put(
        f"/consultations/{consultation_id}/data",
        json={"patient": {"fullName": CANARY, "inconnu": 1}},
        headers=api.headers(),
    )
    assert response.status_code == 422
    assert CANARY not in response.text


# -- F-25 rejoué sur les routes de consultation --------------------------------------------


def test_F25_other_clinician_cannot_list_read_edit_validate_or_redeposit(api: Api) -> None:
    consultation_id = _parsed(api, subject="clin-a")
    other = {"subject": "clin-b"}
    missing = str(uuid4())
    assert api.client.get("/consultations", headers=api.headers(**other)).json() == []
    calls = [
        ("GET", "", {}),
        ("PUT", "/data", {"json": _edit(EXPECTED_CLEAN)}),
        ("POST", "/validate", {}),
        ("POST", "/superbill", {"files": {"file": ("a.pdf", blank_pdf(1))}}),
    ]
    for method, suffix, kwargs in calls:
        foreign = api.client.request(
            method,
            f"/consultations/{consultation_id}{suffix}",
            headers=api.headers(**other),
            **kwargs,
        )
        absent = api.client.request(
            method, f"/consultations/{missing}{suffix}", headers=api.headers(**other), **kwargs
        )
        assert (foreign.status_code, foreign.json()) == (absent.status_code, absent.json())
        assert foreign.status_code == 404
    owner = api.client.get(
        f"/consultations/{consultation_id}", headers=api.headers(subject="clin-a")
    )
    assert owner.json()["state"] == "parsed"


def test_E02_list_shows_only_own_consultations_newest_first(api: Api) -> None:
    first = _parsed(api, subject="clin-a")
    api.clock.advance(timedelta(hours=1))
    second = _parsed(api, subject="clin-a")
    _parsed(api, subject="clin-b")
    rows = api.client.get("/consultations", headers=api.headers(subject="clin-a")).json()
    assert [r["id"] for r in rows] == [second, first]
    assert rows[0]["patient_name"] == "Jane Doe"
