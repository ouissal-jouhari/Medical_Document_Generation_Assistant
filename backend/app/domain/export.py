"""Export clinique et rapport de provenance (F-18, F-23, F-24, L-08). Aucune dépendance externe.

Le document exporté ne reprend que le contenu clinique : bloc commun, sections approuvées et
ligne d'approbation. Origines, sources et marques de brouillon restent dans le rapport séparé.
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.domain.document import NOT_PROVIDED, DocumentState
from app.domain.errors import NotApproved
from app.domain.values import ExportableDocument, ProvenanceEntry, ProvenanceReport

ORIGIN_LABELS = {"ai": "AI", "clinician": "Clinician"}
COMMON_BLOCK_FIELDS = (
    "patient.fullName",
    "patient.dateOfBirth",
    "patient.patientId",
    "physician.name",
    "encounter.dateOfService",
    "diagnoses",
    "procedures",
)


def format_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M UTC")


def ensure_exportable(state: str) -> None:
    """Export PDF possible après approbation seulement (F-18)."""
    if state != DocumentState.APPROVED:
        raise NotApproved


def exportable_document(
    content: dict[str, Any],
    clinic: dict[str, str],
    approver_name: str,
    approved_at: datetime,
) -> ExportableDocument:
    sections = tuple(
        (str(section.get("name")), section.get("content") or None)
        for section in content.get("sections") or []
    )
    return ExportableDocument(
        title=str(content.get("template") or ""),
        clinic=dict(clinic),
        common_block=dict(content.get("common_block") or {}),
        sections=sections,
        approver_name=approver_name,
        approved_at=format_datetime(approved_at),
    )


def _describe(source: Mapping[str, Any], names: Mapping[str, str]) -> str:
    """Une source lisible (SRS 9.3) : extrait du texte avec positions, Superbill, ou auteur et
    date d'une modification."""
    kind = source.get("kind")
    if kind == "clinician":
        author = names.get(str(source.get("author_id")), "unknown clinician")
        return f"Clinician edit by {author} on {source.get('at')}"
    citation = source.get("citation")
    if kind == "consultation_text":
        return (
            f"Consultation text, characters {source.get('start')}-{source.get('end')}: “{citation}”"
        )
    return f"Superbill: “{citation}”"


def provenance_report(
    content: dict[str, Any],
    state: str,
    version: int,
    generated_at: datetime,
    names: Mapping[str, str],
) -> ProvenanceReport:
    """Rapport de provenance par section (F-23, SRS 9.3), avant ou après approbation."""
    entries = [
        ProvenanceEntry(
            section="Patient and encounter",
            status="PROVIDED",
            origin="Superbill",
            sources=tuple(f"Superbill field: {field}" for field in COMMON_BLOCK_FIELDS),
        )
    ]
    for section in content.get("sections") or []:
        entries.append(
            ProvenanceEntry(
                section=str(section.get("name")),
                status=str(section.get("status") or NOT_PROVIDED),
                origin=ORIGIN_LABELS.get(str(section.get("origin")), str(section.get("origin"))),
                sources=tuple(_describe(s, names) for s in section.get("sources") or []),
            )
        )
    return ProvenanceReport(
        title=str(content.get("template") or ""),
        state="Approved" if state == DocumentState.APPROVED else "Under Review",
        version=version,
        generated_at=format_datetime(generated_at),
        entries=tuple(entries),
    )


def clinician_ids(content: dict[str, Any]) -> set[str]:
    """Auteurs des modifications cités dans les sources (noms résolus par le service)."""
    return {
        str(source.get("author_id"))
        for section in content.get("sections") or []
        for source in section.get("sources") or []
        if source.get("kind") == "clinician"
    }
