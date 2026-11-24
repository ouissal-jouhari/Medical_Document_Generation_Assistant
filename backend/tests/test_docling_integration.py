"""Docling réel sur CPU (F-04, I-01) : lancé par le job CI « ocr » (RUN_DOCLING_TESTS=1).

Mesure aussi la durée de l'extraction d'un scan (objectif de 20 s, non bloquant : rapportée).
"""

import json
import os
import time
from pathlib import Path

import pytest

if not os.environ.get("RUN_DOCLING_TESTS"):
    pytest.skip("RUN_DOCLING_TESTS non défini : test Docling ignoré", allow_module_level=True)

from app.adapters.docling_converter import DoclingMarkdownConverter
from app.adapters.extraction import HybridOcrProvider
from app.domain.superbill import REQUIRED_FIELD_COUNT, canonical, missing_required, to_dict
from app.domain.superbill_parser import parse_superbill_text

FIXTURES = Path(__file__).parent / "fixtures" / "superbills"


@pytest.fixture(scope="module")
def provider() -> HybridOcrProvider:
    return HybridOcrProvider(
        DoclingMarkdownConverter(os.environ.get("DOCLING_ARTIFACTS_PATH")), timeout_seconds=900.0
    )


def test_F04_degraded_scan_goes_through_docling_and_yields_fields(
    provider: HybridOcrProvider, capsys: pytest.CaptureFixture[str]
) -> None:
    content = (FIXTURES / "degraded_scan.png").read_bytes()
    started = time.perf_counter()
    result = provider.extract_text(content, "image/png")
    elapsed = time.perf_counter() - started
    with capsys.disabled():
        print(f"\n[mesure] extraction du scan dégradé : {elapsed:.1f} s (objectif 20 s)")
    assert result.engine == "docling"
    data = parse_superbill_text(result.text, result.pages)
    found = REQUIRED_FIELD_COUNT - len(missing_required(data))
    # Un scan dégradé peut perdre des champs : le clinicien corrige (F-05, R-02). On exige que
    # l'extraction ne soit pas un échec total et qu'une majorité de champs soit trouvée.
    assert found >= 4, f"seulement {found}/{REQUIRED_FIELD_COUNT} champs : {missing_required(data)}"


def test_F04_pdf_without_text_layer_is_read_by_docling(provider: HybridOcrProvider) -> None:
    from tests.superbill_samples import blank_pdf

    result = provider.extract_text(blank_pdf(1), "application/pdf")
    assert result.engine == "docling"


def test_F04_clean_pdf_expected_data_is_stable() -> None:
    expected = json.loads((FIXTURES / "clean_superbill.expected.json").read_text(encoding="utf-8"))
    content = (FIXTURES / "clean_superbill.pdf").read_bytes()
    docling = DoclingMarkdownConverter(os.environ.get("DOCLING_ARTIFACTS_PATH"))
    markdown = docling.convert_to_markdown(content, "pdf")
    data = to_dict(canonical(parse_superbill_text(markdown, 1)))
    assert data["patient"] == expected["patient"]
    assert [d["code"] for d in data["diagnoses"]] == [d["code"] for d in expected["diagnoses"]]
