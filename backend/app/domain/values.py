"""Objets-valeurs échangés avec les ports. Aucune dépendance externe."""

from dataclasses import dataclass, field


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
    document_id: str
    template_id: str
    language: str
    sections: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ExportedFile:
    filename: str
    media_type: str
    content: bytes
