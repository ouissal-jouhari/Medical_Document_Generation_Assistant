"""Adaptateurs LLM derrière LlmProvider."""

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GeminiLlmProvider:
    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
        }
        request = Request(  # noqa: S310
            f"{url}?key={self._api_key}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310  # nosec B310
                body = json.loads(response.read().decode("utf-8"))
        except TimeoutError as error:
            raise TimeoutError("llm_timeout") from error
        except (HTTPError, URLError, OSError) as error:
            raise RuntimeError("llm_unavailable") from error
        try:
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            result = json.loads(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise ValueError("malformed_generation") from error
        if not isinstance(result, dict):
            raise ValueError("malformed_generation")
        return result


class OllamaLlmProvider:
    def __init__(self, base_url: str, model: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": schema,
        }
        request = Request(  # noqa: S310
            f"{self._base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310  # nosec B310
                body = json.loads(response.read().decode("utf-8"))
        except TimeoutError as error:
            raise TimeoutError("llm_timeout") from error
        except (HTTPError, URLError, OSError) as error:
            raise RuntimeError("llm_unavailable") from error
        try:
            result = json.loads(body["response"])
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ValueError("malformed_generation") from error
        if not isinstance(result, dict):
            raise ValueError("malformed_generation")
        return result
