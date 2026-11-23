from typing import Protocol

from app.domain.values import Identity


class IdentityProvider(Protocol):
    """Vérifie un jeton d'accès et renvoie l'identité ; lève une erreur si invalide."""

    def verify_token(self, token: str) -> Identity: ...
