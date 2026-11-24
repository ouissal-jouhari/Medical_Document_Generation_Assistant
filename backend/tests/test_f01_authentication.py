"""F-01 / N-04 / N-11 : MFA obligatoire côté API, messages sûrs sans trace technique."""

from pathlib import Path

import pytest

from tests.conftest import CANARY, Api
from tests.helpers_auth import new_rsa_key


def _logs(log_dir: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in log_dir.glob("xeleron.log*"))


def test_F01_request_without_session_is_refused_with_login_required(api: Api) -> None:
    response = api.client.get("/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "authentication_required"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_F01_single_factor_token_is_rejected_by_the_api(api: Api) -> None:
    response = api.client.get("/me", headers=api.headers(acr="1"))
    assert response.status_code == 403
    assert response.json() == {"detail": "mfa_required"}


def test_F01_token_without_acr_claim_is_rejected(api: Api) -> None:
    response = api.client.get("/me", headers=api.headers(acr=""))
    assert response.status_code == 403
    assert response.json() == {"detail": "mfa_required"}


def test_F01_valid_mfa_token_gives_access_and_creates_user(api: Api) -> None:
    response = api.client.get("/me", headers=api.headers(name="Dr Alice"))
    assert response.status_code == 200
    assert response.json()["display_name"] == "Dr Alice"
    again = api.client.get("/me", headers=api.headers(name="Dr Alice Martin"))
    assert again.json()["id"] == response.json()["id"]
    assert again.json()["display_name"] == "Dr Alice Martin"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"expires_in": -60},
        {"issuer": "https://autre.invalid/realms/x"},
        {"azp": "autre-client"},
    ],
)
def test_N11_expired_or_foreign_token_gives_safe_session_error(
    api: Api, kwargs: dict[str, object]
) -> None:
    response = api.client.get("/me", headers=api.headers(**kwargs))
    assert response.status_code == 401
    assert response.json() == {"detail": "session_invalid"}


def test_N11_token_signed_by_another_key_is_rejected(api: Api) -> None:
    from tests.helpers_auth import make_token

    forged = make_token(new_rsa_key())
    response = api.client.get("/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401
    assert response.json() == {"detail": "session_invalid"}


def test_N11_garbage_token_gives_safe_error(api: Api) -> None:
    response = api.client.get("/me", headers={"Authorization": "Bearer pas.un.jeton"})
    assert response.status_code == 401
    assert response.json() == {"detail": "session_invalid"}


def test_N11_identity_provider_unavailable_gives_safe_503(api: Api) -> None:
    api.keys.unavailable = True
    response = api.client.get("/me", headers=api.headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "identity_provider_unavailable"}


def test_N11_forbidden_when_role_is_missing(api: Api) -> None:
    response = api.client.get("/me", headers=api.headers(roles=("visiteur",)))
    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


def test_N11_error_responses_have_no_technical_trace(api: Api) -> None:
    for headers in ({}, api.headers(acr="1"), api.headers(expires_in=-5)):
        body = api.client.get("/me", headers=headers).text
        assert "Traceback" not in body
        assert "jwt" not in body.lower()
        assert 'File "' not in body


def test_N08_canary_name_and_token_never_logged(api: Api, log_dir: Path) -> None:
    token = api.token(name=CANARY)
    api.client.get("/me", headers={"Authorization": f"Bearer {token}"})
    api.client.get("/me", headers=api.headers(name=CANARY, acr="1"))
    api.keys.unavailable = True
    api.client.get("/me", headers=api.headers(name=CANARY))
    logs = _logs(log_dir)
    assert CANARY not in logs
    assert token not in logs
