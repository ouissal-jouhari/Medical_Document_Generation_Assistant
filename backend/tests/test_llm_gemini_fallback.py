"""F-12 : Gemini réessaie puis bascule sur un modèle de repli en cas d'échec."""

import io
import json
from typing import Any
from urllib.error import HTTPError

import pytest

from app.adapters import llm
from app.adapters.llm import GeminiLlmProvider
from app.domain.superbill_parser import parse_superbill_text


class _Response(io.BytesIO):
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _ok(payload: dict[str, Any]) -> _Response:
    body = {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}
    return _Response(json.dumps(body).encode())


def _http_error(code: int) -> HTTPError:
    return HTTPError("https://x", code, "err", {}, None)  # type: ignore[arg-type]


def _provider(
    monkeypatch: pytest.MonkeyPatch, outcomes: list[Any]
) -> tuple[GeminiLlmProvider, list[str]]:
    called: list[str] = []

    def fake_urlopen(request: Any, timeout: float) -> _Response:
        called.append(request.full_url.split("/models/")[1].split(":")[0])
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        assert isinstance(outcome, _Response)
        return outcome

    monkeypatch.setattr(llm, "urlopen", fake_urlopen)
    provider = GeminiLlmProvider("k", "main", 5.0, ("backup",), 2, sleep=lambda _s: None)
    return provider, called


def test_F12_retries_then_falls_back_to_next_model(monkeypatch: pytest.MonkeyPatch) -> None:
    provider, called = _provider(monkeypatch, [_http_error(503), _http_error(503), _ok({"a": "b"})])
    assert provider.generate_structured("p", {}) == {"a": "b"}
    assert called == ["main", "main", "backup"]


def test_F12_unavailable_when_all_models_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    provider, _ = _provider(monkeypatch, [_http_error(503)] * 4)
    with pytest.raises(RuntimeError, match="llm_unavailable"):
        provider.generate_structured("p", {})


def test_F12_api_key_is_sent_in_header_not_url(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Any] = []

    def fake_urlopen(request: Any, timeout: float) -> _Response:
        seen.append(request)
        return _ok({"a": 1})

    monkeypatch.setattr(llm, "urlopen", fake_urlopen)
    GeminiLlmProvider("secret-key", "main", 5.0).generate_structured("p", {})
    assert "secret-key" not in seen[0].full_url
    assert seen[0].get_header("X-goog-api-key") == "secret-key"


def test_F04_ocr_misread_icd_code_and_insurance_label_with_period() -> None:
    text = (
        "Patient Name: Jane Doe\nPatient ID: P-000123 Insurance Provider. Northwind Health\n"
        "Diagnoses\nICD-10 Code Description\n110 Essential (primary) hypertension\n"
    )
    data = parse_superbill_text(text, 1)
    assert data.patient_id == "P-000123"
    assert [d.code for d in data.diagnoses] == ["I10"]


def test_F12_gemini_schema_has_no_unsupported_json_schema_keywords() -> None:
    """Cause du 503 : Gemini rejette (400) `type: [..., "null"]` et `additionalProperties`."""
    from app.adapters.llm import to_gemini_schema
    from app.adapters.templates import load_templates
    from app.services.generation import GenerationService

    template = next(iter(load_templates("app/templates").values()))
    schema = to_gemini_schema(GenerationService(None, None, None, None)._schema(template))  # type: ignore[arg-type]
    dumped = json.dumps(schema)
    assert "additionalProperties" not in dumped
    assert '["string", "null"]' not in dumped
    assert '"nullable": true' in dumped


def test_F12_timeout_falls_back_to_next_model_without_second_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, called = _provider(monkeypatch, [TimeoutError(), _ok({"a": "b"})])
    assert provider.generate_structured("p", {}) == {"a": "b"}
    assert called == ["main", "backup"]
