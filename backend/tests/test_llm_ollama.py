"""F-12 : profil local Ollama (gpt-oss-20b), interchangeable avec Gemini par configuration."""

import io
import json
from typing import Any
from urllib.error import URLError

import pytest

from app.adapters import llm
from app.adapters.llm import GeminiLlmProvider, OllamaLlmProvider
from app.api import deps
from app.core.config import Settings


class _Response(io.BytesIO):
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _ollama_reply(response: str) -> _Response:
    return _Response(json.dumps({"response": response}).encode())


def _patch(monkeypatch: pytest.MonkeyPatch, outcome: Any) -> list[Any]:
    seen: list[Any] = []

    def fake_urlopen(request: Any, timeout: float) -> _Response:
        seen.append((request.full_url, json.loads(request.data), timeout))
        if isinstance(outcome, Exception):
            raise outcome
        assert isinstance(outcome, _Response)
        return outcome

    monkeypatch.setattr(llm, "urlopen", fake_urlopen)
    return seen


def test_F12_ollama_returns_the_structured_object(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _patch(monkeypatch, _ollama_reply('{"sections": []}'))
    provider = OllamaLlmProvider("http://ollama:11434/", "gpt-oss-20b", 30.0)
    assert provider.generate_structured("prompt", {"type": "object"}) == {"sections": []}
    url, payload, timeout = seen[0]
    assert url == "http://ollama:11434/api/generate"
    assert payload["model"] == "gpt-oss-20b"
    assert payload["stream"] is False
    assert payload["format"] == {"type": "object"}
    assert timeout == 30.0


def test_F12_ollama_timeout_is_reported_as_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, TimeoutError())
    with pytest.raises(TimeoutError, match="llm_timeout"):
        OllamaLlmProvider("http://ollama:11434", "gpt-oss-20b", 30.0).generate_structured("p", {})


def test_F12_ollama_unreachable_is_reported_as_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, URLError("connection refused"))
    with pytest.raises(RuntimeError, match="llm_unavailable"):
        OllamaLlmProvider("http://ollama:11434", "gpt-oss-20b", 30.0).generate_structured("p", {})


def test_F12_ollama_malformed_reply_is_a_malformed_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(monkeypatch, _ollama_reply("not json at all"))
    with pytest.raises(ValueError, match="malformed_generation"):
        OllamaLlmProvider("http://ollama:11434", "gpt-oss-20b", 30.0).generate_structured("p", {})


def test_F12_provider_is_chosen_by_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gemini et Ollama sont interchangeables : seul LLM_PROVIDER change."""
    deps.get_llm_provider.cache_clear()
    monkeypatch.setattr(deps, "get_settings", lambda: Settings(llm_provider="ollama"))
    assert isinstance(deps.get_llm_provider(), OllamaLlmProvider)
    deps.get_llm_provider.cache_clear()
    monkeypatch.setattr(deps, "get_settings", lambda: Settings(llm_provider="gemini"))
    assert isinstance(deps.get_llm_provider(), GeminiLlmProvider)
    deps.get_llm_provider.cache_clear()
