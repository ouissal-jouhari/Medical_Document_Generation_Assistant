"""Cycle de vie d'un document (niveau 2 du workflow, SRS section 3) : règles de revue.

Le gel d'un document approuvé est imposé ici, quel que soit l'appelant (interface ou API).
Une version n'est jamais modifiée : toute édition, tout rollback ou toute régénération crée
une nouvelle version, ce qui annule de fait la marque « relu » (portée par une version).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.domain.errors import (
    ApprovalBlocked,
    DocumentApproved,
    ValidationFailed,
    VersionConflict,
    WrongState,
)


class DocumentState(StrEnum):
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"


class VersionKind(StrEnum):
    """Type stocké d'une version. « Rejetée » et « approuvée » sont des marques (SRS 9.1)."""

    AI_GENERATED = "ai_generated"
    EDITED = "edited"


class VersionMark(StrEnum):
    REVIEWED = "reviewed"
    REJECTED = "rejected"


class SectionOrigin(StrEnum):
    """Les 4 origines affichées en revue (F-13) : Superbill et texte via les sources."""

    AI = "ai"
    CLINICIAN = "clinician"


PROVIDED = "PROVIDED"
NOT_PROVIDED = "NOT_PROVIDED"
REQUIRED = "REQUIRED"
SAFETY = "SAFETY"
COMMON_BLOCK_REQUIRED = (
    "patient_name",
    "date_of_birth",
    "patient_id",
    "physician",
    "date_of_service",
    "diagnoses",
    "procedures",
)


@dataclass(frozen=True)
class ReviewSnapshot:
    """État de revue d'un document : état, version courante et ses marques."""

    state: DocumentState
    current_version: int
    current_reviewed: bool
    current_rejected: bool


def ensure_modifiable(snapshot: ReviewSnapshot, expected_version: int) -> None:
    """Toute action de revue : document non approuvé (F-16, F-17) et version attendue (F-14)."""
    if snapshot.state == DocumentState.APPROVED:
        raise DocumentApproved
    if expected_version != snapshot.current_version:
        raise VersionConflict


def ensure_can_mark_reviewed(snapshot: ReviewSnapshot, expected_version: int) -> None:
    ensure_modifiable(snapshot, expected_version)
    if snapshot.current_rejected:
        raise WrongState


def ensure_can_reject(snapshot: ReviewSnapshot, expected_version: int) -> None:
    ensure_modifiable(snapshot, expected_version)
    if snapshot.current_rejected:
        raise WrongState


def ensure_can_regenerate(snapshot: ReviewSnapshot, expected_version: int) -> None:
    """Régénération : seulement après rejet de la version courante (F-15)."""
    ensure_modifiable(snapshot, expected_version)
    if not snapshot.current_rejected:
        raise WrongState


def ensure_can_rollback(snapshot: ReviewSnapshot, expected_version: int, target: int) -> None:
    ensure_modifiable(snapshot, expected_version)
    if target < 1 or target >= snapshot.current_version:
        raise WrongState


def missing_information(content: dict[str, Any]) -> list[dict[str, str]]:
    """Liste « Missing information » (F-13) : sections non fournies et champs du bloc commun."""
    missing: list[dict[str, str]] = []
    block = content.get("common_block") or {}
    for field in COMMON_BLOCK_REQUIRED:
        if not block.get(field):
            missing.append({"name": field, "level": "COMMON"})
    for section in content.get("sections") or []:
        if section.get("status") != PROVIDED:
            missing.append({"name": str(section.get("name")), "level": str(section.get("level"))})
    return missing


def approval_blockers(snapshot: ReviewSnapshot, content: dict[str, Any]) -> list[str]:
    """Éléments qui empêchent l'approbation (F-17, F-26, S-06, S-07). Liste vide = approuvable."""
    blockers: list[str] = []
    if snapshot.current_rejected:
        blockers.append("version_rejected")
    if not snapshot.current_reviewed:
        blockers.append("not_reviewed")
    for item in missing_information(content):
        if item["level"] in ("COMMON", REQUIRED):
            blockers.append(item["name"])
    return blockers


def ensure_can_approve(
    snapshot: ReviewSnapshot, expected_version: int, content: dict[str, Any]
) -> None:
    ensure_modifiable(snapshot, expected_version)
    blockers = approval_blockers(snapshot, content)
    if blockers:
        raise ApprovalBlocked({"missing": blockers})


def apply_edits(
    content: dict[str, Any],
    edits: dict[str, str | None],
    author_id: UUID,
    at: datetime,
) -> dict[str, Any] | None:
    """Nouveau contenu après édition (F-14). None si rien ne change (aucune version créée).

    Une section éditée avec un contenu non vide devient fournie, d'origine clinicien ; vidée,
    elle redevient « Not provided ». Le bloc commun (Superbill validée) n'est pas éditable.
    """
    sections = [dict(section) for section in content.get("sections") or []]
    names = {str(section.get("name")) for section in sections}
    unknown = sorted(set(edits) - names)
    if unknown:
        raise ValidationFailed(
            {
                "issues": [
                    {"field": name, "code": "unknown_section", "blocking": True} for name in unknown
                ]
            }
        )
    changed = False
    for section in sections:
        name = str(section.get("name"))
        if name not in edits:
            continue
        text = (edits[name] or "").strip()
        new_content = text or None
        if new_content == section.get("content"):
            continue
        changed = True
        section["content"] = new_content
        section["status"] = PROVIDED if new_content else NOT_PROVIDED
        section["origin"] = SectionOrigin.CLINICIAN.value
        section["sources"] = [
            {
                "kind": SectionOrigin.CLINICIAN.value,
                "author_id": str(author_id),
                "at": at.isoformat(),
            }
        ]
    if not changed:
        return None
    return {**content, "sections": sections}
