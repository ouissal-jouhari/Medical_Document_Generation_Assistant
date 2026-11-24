"""Règle de décision de l'extraction (ADR 0007) : texte direct si complet, sinon Docling."""

import threading
import time

import pytest

from app.adapters.extraction import HybridOcrProvider
from app.domain.errors import ExtractionError
from tests.superbill_samples import CLEAN_TEXT, blank_pdf, image_bytes, pdf_with_text


class FakeDocling:
    def __init__(self, markdown: str = "| Patient Name | Jane Doe |", delay: float = 0.0) -> None:
        self.markdown = markdown
        self.delay = delay
        self.calls: list[str] = []
        self.thread_names: list[str] = []
        self.error: Exception | None = None

    def convert_to_markdown(self, content: bytes, suffix: str) -> str:
        self.calls.append(suffix)
        self.thread_names.append(threading.current_thread().name)
        if self.delay:
            time.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return self.markdown


def test_F04_pdf_with_complete_text_layer_skips_docling() -> None:
    docling = FakeDocling()
    result = HybridOcrProvider(docling).extract_text(pdf_with_text(CLEAN_TEXT), "application/pdf")
    assert result.engine == "text-layer"
    assert docling.calls == []


def test_F04_pdf_without_text_layer_goes_through_docling() -> None:
    docling = FakeDocling()
    result = HybridOcrProvider(docling).extract_text(blank_pdf(2), "application/pdf")
    assert (result.engine, result.pages) == ("docling", 2)
    assert docling.calls == ["pdf"]


def test_F04_pdf_with_incomplete_text_layer_goes_through_docling() -> None:
    incomplete = "Patient Name: Jane Doe\nDate of Service: 11/20/2026\n"
    docling = FakeDocling()
    result = HybridOcrProvider(docling).extract_text(pdf_with_text(incomplete), "application/pdf")
    assert result.engine == "docling"
    assert docling.calls == ["pdf"]


@pytest.mark.parametrize(
    ("fmt", "content_type", "suffix"),
    [
        ("PNG", "image/png", "png"),
        ("JPEG", "image/jpeg", "jpeg"),
    ],
)
def test_F04_images_always_go_through_docling(fmt: str, content_type: str, suffix: str) -> None:
    docling = FakeDocling()
    result = HybridOcrProvider(docling).extract_text(image_bytes(fmt), content_type)
    assert (result.engine, result.pages) == ("docling", 1)
    assert docling.calls == [suffix]


def test_F04_docling_runs_outside_the_calling_thread() -> None:
    docling = FakeDocling()
    HybridOcrProvider(docling).extract_text(blank_pdf(1), "application/pdf")
    assert docling.thread_names[0].startswith("docling")
    assert docling.thread_names[0] != threading.current_thread().name


def test_F06_docling_failure_becomes_an_extraction_error() -> None:
    docling = FakeDocling()
    docling.error = RuntimeError("détail technique")
    with pytest.raises(ExtractionError):
        HybridOcrProvider(docling).extract_text(blank_pdf(1), "application/pdf")


def test_F06_docling_timeout_becomes_an_extraction_error() -> None:
    docling = FakeDocling(delay=1.0)
    with pytest.raises(ExtractionError):
        HybridOcrProvider(docling, timeout_seconds=0.05).extract_text(
            blank_pdf(1), "application/pdf"
        )
