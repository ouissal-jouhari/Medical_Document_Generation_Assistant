"""Superbill normalisée (SRS 9.2) et validation déterministe (F-04, F-05, R-02).

Les valeurs restent des chaînes : pendant la correction, une valeur peut être invalide ; la
validation la signale sans jamais la modifier. Aucune dépendance externe.
"""

import re
from collections.abc import Container
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ICD10CM = re.compile(r"^[A-TV-Z][0-9][0-9AB](\.[0-9A-TV-Z]{1,4})?$")
CPT = re.compile(r"^(\d{5}|\d{4}[FT])$")
AMOUNT = re.compile(r"^\$?\d{1,3}(,?\d{3})*(\.\d{1,2})?$")


@dataclass(frozen=True)
class Diagnosis:
    code: str = ""
    description: str = ""


@dataclass(frozen=True)
class Procedure:
    code: str = ""
    description: str = ""
    units: int | None = None


@dataclass(frozen=True)
class SuperbillData:
    patient_full_name: str | None = None
    patient_date_of_birth: str | None = None
    patient_id: str | None = None
    physician_name: str | None = None
    date_of_service: str | None = None
    place_of_service: str | None = None
    diagnoses: tuple[Diagnosis, ...] = ()
    procedures: tuple[Procedure, ...] = ()
    total_charges: str | None = None
    page_count: int = 0


@dataclass(frozen=True)
class Issue:
    """Problème de validation. Ne contient jamais la valeur saisie (N-11)."""

    field: str
    code: str
    blocking: bool


def normalize_icd(code: str) -> str:
    return code.strip().upper()


def is_valid_date(value: str) -> bool:
    if not ISO_DATE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _blank(value: str | None) -> bool:
    return value is None or not value.strip()


REQUIRED_FIELD_COUNT = 7


def missing_required(data: SuperbillData) -> list[str]:
    """Champs obligatoires absents (présence seulement, pas le format)."""
    checks = {
        "patient.fullName": not _blank(data.patient_full_name),
        "patient.dateOfBirth": not _blank(data.patient_date_of_birth),
        "patient.patientId": not _blank(data.patient_id),
        "physician.name": not _blank(data.physician_name),
        "encounter.dateOfService": not _blank(data.date_of_service),
        "diagnoses": any(not _blank(d.code) for d in data.diagnoses),
        "procedures": any(not _blank(p.code) for p in data.procedures),
    }
    return [name for name, present in checks.items() if not present]


def required_fields_present(data: SuperbillData) -> bool:
    return not missing_required(data)


def validate(data: SuperbillData, known_icd: Container[str] | None) -> list[Issue]:
    issues: list[Issue] = []

    def need(name: str, value: str | None) -> bool:
        if _blank(value):
            issues.append(Issue(name, "required_missing", True))
            return False
        return True

    need("patient.fullName", data.patient_full_name)
    need("patient.patientId", data.patient_id)
    need("physician.name", data.physician_name)
    for name, value in (
        ("patient.dateOfBirth", data.patient_date_of_birth),
        ("encounter.dateOfService", data.date_of_service),
    ):
        if need(name, value) and not is_valid_date((value or "").strip()):
            issues.append(Issue(name, "invalid_date", True))
    if not data.diagnoses:
        issues.append(Issue("diagnoses", "required_missing", True))
    if not data.procedures:
        issues.append(Issue("procedures", "required_missing", True))
    for i, diagnosis in enumerate(data.diagnoses):
        name = f"diagnoses[{i}].code"
        if _blank(diagnosis.code):
            issues.append(Issue(name, "required_missing", True))
        elif not ICD10CM.match(normalize_icd(diagnosis.code)):
            issues.append(Issue(name, "invalid_icd10cm_format", True))
        elif known_icd is not None and normalize_icd(diagnosis.code).replace(".", "") not in known_icd:
            issues.append(Issue(name, "icd10cm_unknown", False))
    for i, procedure in enumerate(data.procedures):
        name = f"procedures[{i}].code"
        if _blank(procedure.code):
            issues.append(Issue(name, "required_missing", True))
        elif not CPT.match(procedure.code.strip().upper()):
            issues.append(Issue(name, "invalid_cpt_format", True))
        if procedure.units is None:
            issues.append(Issue(f"procedures[{i}].units", "units_missing", False))
        elif procedure.units < 1:
            issues.append(Issue(f"procedures[{i}].units", "invalid_units", True))
    if not _blank(data.total_charges) and not AMOUNT.match((data.total_charges or "").strip()):
        issues.append(Issue("billing.totalCharges", "invalid_amount", False))
    return issues


def canonical(data: SuperbillData) -> SuperbillData:
    """Normalise la casse et les espaces des codes ; les valeurs ne sont jamais corrigées."""
    return replace(
        data,
        diagnoses=tuple(
            Diagnosis(normalize_icd(d.code), d.description.strip()) for d in data.diagnoses
        ),
        procedures=tuple(
            Procedure(p.code.strip().upper(), p.description.strip(), p.units)
            for p in data.procedures
        ),
    )


def has_blocking_issue(issues: list[Issue]) -> bool:
    return any(issue.blocking for issue in issues)


def to_dict(data: SuperbillData) -> dict[str, Any]:
    """Forme JSON stockée et exposée (clés du schéma 9.2)."""
    return {
        "patient": {
            "fullName": data.patient_full_name,
            "dateOfBirth": data.patient_date_of_birth,
            "patientId": data.patient_id,
        },
        "physician": {"name": data.physician_name},
        "encounter": {
            "dateOfService": data.date_of_service,
            "placeOfService": data.place_of_service,
        },
        "diagnoses": [{"code": d.code, "description": d.description} for d in data.diagnoses],
        "procedures": [
            {"code": p.code, "description": p.description, "units": p.units}
            for p in data.procedures
        ],
        "billing": {"totalCharges": data.total_charges},
        "extraction": {"pageCount": data.page_count},
    }


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _units(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0  # valeur illisible : signalée par la validation (invalid_units)


def from_dict(raw: dict[str, Any]) -> SuperbillData:
    patient = raw.get("patient") or {}
    encounter = raw.get("encounter") or {}
    return SuperbillData(
        patient_full_name=_text(patient.get("fullName")),
        patient_date_of_birth=_text(patient.get("dateOfBirth")),
        patient_id=_text(patient.get("patientId")),
        physician_name=_text((raw.get("physician") or {}).get("name")),
        date_of_service=_text(encounter.get("dateOfService")),
        place_of_service=_text(encounter.get("placeOfService")),
        diagnoses=tuple(
            Diagnosis(_text(d.get("code")) or "", _text(d.get("description")) or "")
            for d in raw.get("diagnoses") or []
        ),
        procedures=tuple(
            Procedure(
                _text(p.get("code")) or "", _text(p.get("description")) or "", _units(p.get("units"))
            )
            for p in raw.get("procedures") or []
        ),
        total_charges=_text((raw.get("billing") or {}).get("totalCharges")),
        page_count=int((raw.get("extraction") or {}).get("pageCount") or 0),
    )


def flatten(raw: dict[str, Any]) -> dict[str, Any]:
    """Aplatit en chemins (ex. diagnoses[0].code) pour tracer chaque correction (F-05)."""
    flat: dict[str, Any] = {}

    def walk(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                walk(f"{prefix}.{key}" if prefix else key, item)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(f"{prefix}[{index}]", item)
        else:
            flat[prefix] = value

    walk("", raw)
    return flat


@dataclass(frozen=True)
class FieldChange:
    path: str
    old: Any
    new: Any


def diff(old: dict[str, Any], new: dict[str, Any]) -> list[FieldChange]:
    before, after = flatten(old), flatten(new)
    changes = []
    for path in sorted(before.keys() | after.keys()):
        if path.startswith("extraction."):
            continue  # métadonnée technique, non modifiable
        if before.get(path) != after.get(path):
            changes.append(FieldChange(path, before.get(path), after.get(path)))
    return changes

