"""N-13 : OCR, LLM, identité, entrée du texte et export sont derrière une interface.

Revue de conception automatisée : le domaine et les ports n'importent aucun adaptateur
ni bibliothèque externe ; un faux fournisseur suffit à satisfaire chaque port.
"""

import ast
from pathlib import Path
from typing import Any

from app.domain.values import (
    ExportableDocument,
    ExportedFile,
    Identity,
    OcrResult,
    Transcript,
)
from app.ports import (
    DocumentExporter,
    IdentityProvider,
    LlmProvider,
    OcrProvider,
    TranscriptIngestion,
)

APP = Path(__file__).resolve().parents[1] / "app"
STDLIB_OK = {"dataclasses", "datetime", "typing", "app", "__future__"}


def _imports(package: str) -> set[str]:
    found: set[str] = set()
    for path in (APP / package).rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                found.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module)
    return found


def test_N13_domain_has_no_external_dependency() -> None:
    imports = _imports("domain")
    assert {m for m in imports if m.split(".")[0] not in STDLIB_OK} == set()
    assert not {m for m in imports if m.startswith("app.adapters")}


def test_N13_ports_depend_only_on_domain() -> None:
    for module in _imports("ports"):
        assert module.split(".")[0] in STDLIB_OK
        assert not module.startswith("app.adapters")
        assert not module.startswith("app.api")


class FakeOcr:
    def extract_text(self, content: bytes, content_type: str) -> OcrResult:
        return OcrResult(text="x", pages=1, engine="fake")


class FakeLlm:
    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        return {}


class FakeIdentity:
    def verify_token(self, token: str) -> Identity:
        return Identity(subject="u", display_name="U", roles=("clinician",), mfa_verified=True)


class FakeTranscript:
    def ingest(self, consultation_id: str, text: str) -> Transcript:
        return Transcript(consultation_id=consultation_id, text=text, source="fake")


class FakeExporter:
    def export(self, document: ExportableDocument) -> ExportedFile:
        return ExportedFile(filename="d.bin", media_type="application/octet-stream", content=b"")


def test_N13_any_provider_satisfies_its_port() -> None:
    ocr: OcrProvider = FakeOcr()
    llm: LlmProvider = FakeLlm()
    identity: IdentityProvider = FakeIdentity()
    ingestion: TranscriptIngestion = FakeTranscript()
    exporter: DocumentExporter = FakeExporter()
    assert ocr.extract_text(b"", "application/pdf").engine == "fake"
    assert llm.generate_structured("p", {}) == {}
    assert identity.verify_token("t").mfa_verified
    assert ingestion.ingest("c", "t").source == "fake"
    assert exporter.export(ExportableDocument("d", "t", "fr")).filename == "d.bin"
