"""Aides de test : jetons OIDC signés avec une clé de test, fournisseur de clés factice."""

import time
from dataclasses import dataclass
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://test.invalid/auth/realms/xeleron"
CLIENT_ID = "xeleron-web"
MFA_ACR = "2"


def new_rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@dataclass
class _Key:
    key: Any


class FakeKeys:
    """Source de clés de signature : valide les jetons signés par `private_key`."""

    def __init__(self, private_key: rsa.RSAPrivateKey, unavailable: bool = False) -> None:
        self._public = private_key.public_key()
        self.unavailable = unavailable

    def get_signing_key_from_jwt(self, token: str) -> _Key:
        if self.unavailable:
            raise jwt.PyJWKClientConnectionError("indisponible")
        return _Key(self._public)


def make_token(
    private_key: rsa.RSAPrivateKey,
    subject: str = "user-a",
    name: str = "Dr Test",
    acr: str = MFA_ACR,
    roles: tuple[str, ...] = ("clinician",),
    issuer: str = ISSUER,
    azp: str = CLIENT_ID,
    expires_in: int = 300,
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": subject,
        "name": name,
        "iss": issuer,
        "azp": azp,
        "acr": acr,
        "iat": now,
        "exp": now + expires_in,
        "realm_access": {"roles": list(roles)},
    }
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test"})
