from typing import Protocol

from app.domain.values import Transcript


class TranscriptIngestion(Protocol):
    """Entrée du texte de consultation (saisie au MVP, AI Scribe plus tard)."""

    def ingest(self, consultation_id: str, text: str) -> Transcript: ...
