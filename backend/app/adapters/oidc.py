"""Adaptateur IdentityProvider pour Keycloak (OIDC).

Le MFA est attesté par la claim `acr` du jeton : Keycloak l'émet au niveau requis seulement
après le second facteur (voir docs/adr/0005). Un jeton mono-facteur donne mfa_verified=False.
"""

from typing import Any, Protocol

import jwt

from app.domain.errors import IdentityProviderUnavailable, InvalidSession
from app.domain.values import Identity


class SigningKey(Protocol):
    @property
    def key(self) -> Any: ...


class SigningKeySource(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> SigningKey: ...


class OidcIdentityProvider:
    def __init__(
        self,
        issuer: str,
        client_id: str,
        required_acr: str,
        keys: SigningKeySource,
    ) -> None:
        self._issuer = issuer
        self._client_id = client_id
        self._required_acr = required_acr
        self._keys = keys

    @classmethod
    def from_jwks_url(
        cls, issuer: str, jwks_url: str, client_id: str, required_acr: str
    ) -> "OidcIdentityProvider":
        return cls(issuer, client_id, required_acr, jwt.PyJWKClient(jwks_url, timeout=5))

    def verify_token(self, token: str) -> Identity:
        try:
            signing_key = self._keys.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self._issuer,
                options={"require": ["exp", "iat", "iss", "sub"], "verify_aud": False},
            )
        except jwt.PyJWKClientConnectionError as exc:
            raise IdentityProviderUnavailable from exc
        except jwt.PyJWTError as exc:
            raise InvalidSession from exc
        if claims.get("azp") != self._client_id:
            raise InvalidSession
        realm_access = claims.get("realm_access")
        roles = tuple(realm_access.get("roles", ())) if isinstance(realm_access, dict) else ()
        display_name = claims.get("name") or claims.get("preferred_username") or "Clinicien"
        return Identity(
            subject=str(claims["sub"]),
            display_name=str(display_name),
            roles=roles,
            mfa_verified=claims.get("acr") == self._required_acr,
        )
