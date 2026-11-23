"""N-08 / N-05 : la valeur-canari n'apparaît ni dans les logs ni dans les erreurs."""

from pathlib import Path

import structlog
from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from tests.conftest import CANARY


class Payload(BaseModel):
    age: int


def _read_logs(log_dir: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in log_dir.glob("xeleron.log*"))


def _add_routes(client: TestClient) -> None:
    router = APIRouter()

    @router.post("/_t/validate")
    def validate(payload: Payload) -> dict[str, int]:
        return {"age": payload.age}

    @router.get("/_t/boom")
    def boom() -> None:
        raise RuntimeError(f"échec pour {CANARY}")

    @router.get("/_t/log")
    def log_it() -> dict[str, str]:
        structlog.get_logger().info("evt", patient_name=CANARY, text=CANARY, note="ok")
        return {"ok": "1"}

    client.app.include_router(router)  # type: ignore[attr-defined]


def test_N08_validation_error_does_not_echo_input(client: TestClient, log_dir: Path) -> None:
    _add_routes(client)
    response = client.post("/_t/validate", json={"age": CANARY})
    assert response.status_code == 422
    assert CANARY not in response.text
    assert CANARY not in _read_logs(log_dir)


def test_N08_unhandled_error_does_not_leak_message(client: TestClient, log_dir: Path) -> None:
    _add_routes(client)
    response = client.get("/_t/boom")
    assert response.status_code == 500
    assert response.json() == {"detail": "internal_error"}
    assert CANARY not in response.text
    assert CANARY not in _read_logs(log_dir)


def test_N08_sensitive_log_keys_are_redacted(client: TestClient, log_dir: Path) -> None:
    _add_routes(client)
    assert client.get("/_t/log").status_code == 200
    logs = _read_logs(log_dir)
    assert "evt" in logs
    assert CANARY not in logs


def test_N08_canary_in_url_and_query_not_logged(client: TestClient, log_dir: Path) -> None:
    client.get(f"/health?name={CANARY}")
    client.get(f"/inconnu/{CANARY}")
    assert CANARY not in _read_logs(log_dir)


def test_N05_http_error_response_has_no_detail_from_input(client: TestClient) -> None:
    response = client.get(f"/inconnu/{CANARY}")
    assert response.status_code == 404
    assert CANARY not in response.text
