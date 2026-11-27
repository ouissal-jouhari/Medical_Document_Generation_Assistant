"""Adaptateurs LLM derrière LlmProvider."""

import json
import time
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import structlog

logger = structlog.get_logger("llm")


def _gemini_error(error: HTTPError, api_key: str) -> tuple[str, str]:
    """Statut et message court renvoyés par Gemini (sans clé ; jamais le prompt ni la réponse)."""
    try:
        detail = json.loads(error.read().decode("utf-8", errors="replace"))["error"]
        status, message = str(detail.get("status", "")), str(detail.get("message", ""))
    except (ValueError, KeyError, TypeError, AttributeError, OSError):
        return "", ""
    return status[:40], message.replace(api_key, "[REDACTED]")[:200] if api_key else message[:200]


def to_gemini_schema(schema: Any) -> Any:
    """JSON Schema standard -> dialecte `responseSchema` de Gemini : pas de `additionalProperties`,
    et un type `["string", "null"]` devient `"string"` + `nullable`."""
    if isinstance(schema, list):
        return [to_gemini_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    converted: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "additionalProperties":
            continue
        if key == "type" and isinstance(value, list):
            kinds = [kind for kind in value if kind != "null"]
            converted["type"] = kinds[0] if kinds else "string"
            if "null" in value:
                converted["nullable"] = True
            continue
        converted[key] = value if key == "enum" else to_gemini_schema(value)
    return converted


class GeminiLlmProvider:
    """Gemini : nouvelle tentative brève puis modèles de repli si le service est surchargé."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        fallback_models: tuple[str, ...] = (),
        attempts_per_model: int = 2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key
        self._models = (model, *(m for m in fallback_models if m != model))
        self._timeout_seconds = timeout_seconds
        self._attempts = attempts_per_model
        self._sleep = sleep

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": to_gemini_schema(schema),
            },
        }
        failure: Exception | None = None
        for model in self._models:
            for attempt in range(self._attempts):
                try:
                    body = self._call(model, payload)
                except _Retryable as error:
                    failure = error
                    if error.fatal:
                        raise RuntimeError("llm_unavailable") from error
                    if error.timeout:
                        break  # modèle trop lent : repli immédiat plutôt qu'une 2e attente
                    if attempt + 1 < self._attempts:
                        self._sleep(1.5 * (attempt + 1))
                    continue
                return self._parse(body)
        if isinstance(failure, _Retryable) and failure.timeout:
            raise TimeoutError("llm_timeout") from failure
        raise RuntimeError("llm_unavailable") from failure

    def _call(self, model: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        request = Request(  # noqa: S310
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": self._api_key},
            method="POST",
        )
        started = time.monotonic()

        def log(outcome: str, **extra: Any) -> None:
            logger.info(
                "llm_attempt",
                provider="gemini",
                model=model,
                outcome=outcome,
                duration_ms=round((time.monotonic() - started) * 1000),
                **extra,
            )

        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310  # nosec B310
                body: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        except TimeoutError as error:
            log("timeout", error_type="TimeoutError")
            raise _Retryable(timeout=True) from error
        except HTTPError as error:
            status, message = _gemini_error(error, self._api_key)
            log(
                "http_error",
                http_status=error.code,
                error_type="HTTPError",
                gemini_status=status,
                gemini_message=message,
            )
            # 400/401/403 : requête ou clé invalide, identique pour tous les modèles (pas de repli).
            raise _Retryable(timeout=False, fatal=error.code in {400, 401, 403}) from error
        except (URLError, OSError, ValueError) as error:
            log("network_error", error_type=type(error).__name__)
            raise _Retryable(timeout=False) from error
        log("ok", http_status=200, **self._finish_info(body))
        return body

    @staticmethod
    def _finish_info(body: dict[str, Any]) -> dict[str, Any]:
        candidates = body.get("candidates") or []
        feedback = body.get("promptFeedback") or {}
        return {
            "finish_reason": candidates[0].get("finishReason") if candidates else "NO_CANDIDATE",
            "block_reason": feedback.get("blockReason"),
        }

    @staticmethod
    def _parse(body: dict[str, Any]) -> dict[str, Any]:
        try:
            parts = body["candidates"][0]["content"]["parts"]
            text = "".join(p["text"] for p in parts if not p.get("thought") and "text" in p)
            result = json.loads(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            logger.info(
                "llm_parse_failed",
                provider="gemini",
                error_type=type(error).__name__,
                **GeminiLlmProvider._finish_info(body),
            )
            raise ValueError("malformed_generation") from error
        if not isinstance(result, dict):
            raise ValueError("malformed_generation")
        return result


class _Retryable(Exception):  # noqa: N818
    def __init__(self, timeout: bool, fatal: bool = False) -> None:
        super().__init__("llm_call_failed")
        self.timeout = timeout
        self.fatal = fatal


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
