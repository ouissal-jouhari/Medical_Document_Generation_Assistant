from typing import Protocol

from app.domain.values import OcrResult


class OcrProvider(Protocol):
    """Extraction du texte d'une Superbill (texte direct, puis OCR si nécessaire)."""

    def extract_text(self, content: bytes, content_type: str) -> OcrResult: ...
