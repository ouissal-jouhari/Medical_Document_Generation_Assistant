"""F-04 : extraction déterministe vers le schéma 9.2 ; validation de format (R-02, P9)."""

import json
from pathlib import Path

from app.adapters.extraction import HybridOcrProvider
from app.adapters.icd_table import load_known_icd
from app.domain.superbill import (
    Diagnosis,
    Procedure,
    SuperbillData,
    canonical,
    diff,
    from_dict,
    has_blocking_issue,
    missing_required,
    to_dict,
    validate,
)
from app.domain.superbill_parser import normalize_date, parse_superbill_text
from tests.superbill_samples import CLEAN_TEXT, EXPECTED_CLEAN, MARKDOWN_TEXT

FIXTURES = Path(__file__).parent / "fixtures" / "superbills"


def test_F04_clean_text_is_extracted_to_the_schema() -> None:
    data = parse_superbill_text(CLEAN_TEXT, page_count=1)
    assert to_dict(canonical(data)) == EXPECTED_CLEAN
    assert missing_required(data) == []


def test_F04_docling_markdown_tables_are_extracted() -> None:
    data = parse_superbill_text(MARKDOWN_TEXT, page_count=1)
    assert data.patient_full_name == "Jane Doe"
    assert data.patient_date_of_birth == "1980-04-12"
    assert data.patient_id == "P-000123"
    assert data.physician_name == "Dr. Alice Martin"
    assert data.date_of_service == "2026-11-20"
    assert [d.code for d in data.diagnoses] == ["E11.9", "I10"]
    assert [(p.code, p.units) for p in data.procedures] == [("99213", 1)]
    assert data.total_charges == "$150.00"


def test_F04_insurance_and_contact_labels_do_not_leak_into_other_fields() -> None:
    text = (
        "Patient Name: Jane Doe Phone: 555-0100 Patient ID: P-9 Insurance Provider: Acme\n"
        "Physician: Dr. Bob Address: 1 Main St Date of Service: 11/20/2026\n"
    )
    data = parse_superbill_text(text, 1)
    assert data.patient_full_name == "Jane Doe"
    assert data.patient_id == "P-9"
    assert data.physician_name == "Dr. Bob"


def test_F04_without_a_units_column_units_are_not_invented() -> None:
    text = "Procedures\n99213 Office visit level 3\n"
    procedures = parse_superbill_text(text, 1).procedures
    assert procedures == (Procedure("99213", "Office visit level 3", None),)


def test_F04_text_without_any_field_finds_nothing() -> None:
    data = parse_superbill_text("Texte sans rapport avec une Superbill.\nBonjour.", 1)
    assert len(missing_required(data)) == 7


def test_F04_clean_pdf_fixture_matches_expected_data() -> None:
    """Superbill synthétique de test : couche texte lue par pypdf, sans Docling."""
    content = (FIXTURES / "clean_superbill.pdf").read_bytes()
    result = HybridOcrProvider(docling=_NeverCalled()).extract_text(content, "application/pdf")
    assert result.engine == "text-layer"
    expected = json.loads((FIXTURES / "clean_superbill.expected.json").read_text(encoding="utf-8"))
    assert to_dict(canonical(parse_superbill_text(result.text, result.pages))) == expected


class _NeverCalled:
    def convert_to_markdown(self, content: bytes, suffix: str) -> str:
        raise AssertionError("Docling ne doit pas être appelé quand le texte direct suffit")


def test_F04_dates_are_normalized_to_iso() -> None:
    assert normalize_date("04/12/1980") == "1980-04-12"
    assert normalize_date("4-2-2026") == "2026-04-02"
    assert normalize_date("April 12, 1980") == "1980-04-12"
    assert normalize_date("2026-11-20") == "2026-11-20"
    assert normalize_date("31/31/2026") == "31/31/2026"  # illisible : laissé tel quel, signalé


def _complete() -> SuperbillData:
    return SuperbillData(
        patient_full_name="Jane Doe",
        patient_date_of_birth="1980-04-12",
        patient_id="P-1",
        physician_name="Dr. A",
        date_of_service="2026-11-20",
        diagnoses=(Diagnosis("E11.9", "x"),),
        procedures=(Procedure("99213", "y", 1),),
        page_count=1,
    )


def test_F04_complete_data_has_no_blocking_issue() -> None:
    assert not has_blocking_issue(validate(_complete(), load_known_icd()))


def test_R02_invalid_formats_are_blocking_and_never_echo_the_value() -> None:
    data = SuperbillData(
        patient_full_name="Jane",
        patient_date_of_birth="12/04/1980",
        patient_id="P",
        physician_name="D",
        date_of_service="2026-13-40",
        diagnoses=(Diagnosis("I1O.9", ""),),  # lettre O au lieu du zéro : erreur d'OCR typique
        procedures=(Procedure("9921", "", 0),),
    )
    issues = {(i.field, i.code) for i in validate(data, None) if i.blocking}
    assert ("patient.dateOfBirth", "invalid_date") in issues
    assert ("encounter.dateOfService", "invalid_date") in issues
    assert ("diagnoses[0].code", "invalid_icd10cm_format") in issues
    assert ("procedures[0].code", "invalid_cpt_format") in issues
    assert ("procedures[0].units", "invalid_units") in issues


def test_P9_unknown_icd_code_is_a_non_blocking_warning() -> None:
    known = load_known_icd()
    assert "E119" in known and "I10" in known
    data = SuperbillData(**{**_complete().__dict__, "diagnoses": (Diagnosis("Z99.99", ""),)})
    warnings = [i for i in validate(data, known) if i.code == "icd10cm_unknown"]
    assert len(warnings) == 1 and not warnings[0].blocking
    assert not has_blocking_issue(validate(data, known))


def test_F04_required_fields_missing_are_reported() -> None:
    codes = {(i.field, i.code) for i in validate(SuperbillData(), None)}
    assert ("patient.fullName", "required_missing") in codes
    assert ("diagnoses", "required_missing") in codes
    assert ("procedures", "required_missing") in codes


def test_F05_diff_lists_changed_paths_without_technical_metadata() -> None:
    before = to_dict(_complete())
    after = to_dict(_complete())
    after["patient"]["fullName"] = "Jane Roe"
    after["diagnoses"].append({"code": "I10", "description": ""})
    after["extraction"]["pageCount"] = 9
    paths = {c.path for c in diff(before, after)}
    assert paths == {
        "patient.fullName",
        "diagnoses[1].code",
        "diagnoses[1].description",
    }
    assert from_dict(before) == _complete()
