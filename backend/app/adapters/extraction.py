"""Adaptateur OcrProvider : texte direct puis Docling (CPU) si nécessaire (ADR 0007).

Règle de décision explicite pour un PDF :
1. extraire la couche texte ;
2. si elle est non vide ET que tous les champs obligatoires s'y trouvent (parsing déterministe),
   le texte direct est utilisé ;
3. sinon (scan, couche texte vide ou incomplète) : Docling.
Une image passe toujours par Docling. Docling s'exécute dans un thread dédié, jamais dans la
boucle d'événements, un seul à la fois (CPU).
"""

import io
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Protocol

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.domain.errors import ExtractionError
from app.domain.superbill import required_fields_present
from app.domain.superbill_parser import parse_superbill_text
from app.domain.values import OcrResult

PDF = "application/pdf"


class DoclingConverter(Protocol):
    """Convertit un document en texte structuré (Markdown). `suffix` : pdf, png ou jpeg."""

    def convert_to_markdown(self, content: bytes, suffix: str) -> str: ...


def pdf_text_layer(content: bytes) -> tuple[str, int]:
    try:
        reader = PdfReader(io.BytesIO(content))
        pages = len(reader.pages)
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except (PyPdfError, ValueError, OSError, KeyError, RecursionError) as exc:
        raise ExtractionError from exc
    return text, pages


class HybridOcrProvider:
    def __init__(self, docling: DoclingConverter, timeout_seconds: float = 300.0) -> None:
        self._docling = docling
        self._timeout = timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="docling")

    def extract_text(self, content: bytes, content_type: str) -> OcrResult:
        pages = 1
        if content_type == PDF:
            text, pages = pdf_text_layer(content)
            if text.strip() and required_fields_present(parse_superbill_text(text, pages)):
                return OcrResult(text=text, pages=pages, engine="text-layer")
        suffix = "pdf" if content_type == PDF else content_type.rsplit("/", 1)[-1]
        future = self._executor.submit(self._docling.convert_to_markdown, content, suffix)
        try:
            markdown = future.result(timeout=self._timeout)
        except FutureTimeout as exc:
            future.cancel()
            raise ExtractionError from exc
        except Exception as exc:
            raise ExtractionError from exc
        return OcrResult(text=markdown, pages=pages, engine="docling")
