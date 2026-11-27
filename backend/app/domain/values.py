"""Objets-valeurs échangés avec les ports. Aucune dépendance externe."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OcrResult:
    text: str
    pages: int
    engine: str


@dataclass(frozen=True)
class Identity:
    subject: str
    display_name: str
    roles: tuple[str, ...]
    mfa_verified: bool


@dataclass(frozen=True)
class Transcript:
    consultation_id: str
    text: str
    source: str


@dataclass(frozen=True)
class ExportableDocument:
    """Document approuvé tel qu'il est exporté (F-18, F-24) : aucune origine, source ni marque
    de brouillon. Les coordonnées de la clinique sont celles figées à l'approbation (H-02)."""

    title: str
    clinic: dict[str, str]
    common_block: dict[str, Any]
    sections: tuple[tuple[str, str | None], ...]
    approver_name: str
    approved_at: str


@dataclass(frozen=True)
class ProvenanceEntry:
    """Une ligne du rapport de provenance (SRS 9.3) : section, statut, origine, sources."""

    section: str
    status: str
    origin: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class ProvenanceReport:
    """Rapport de provenance séparé du document clinique (F-23, L-08)."""

    title: str
    state: str
    version: int
    generated_at: str
    entries: tuple[ProvenanceEntry, ...]


@dataclass(frozen=True)
class ExportedFile:
    filename: str
    media_type: str
    content: bytes
