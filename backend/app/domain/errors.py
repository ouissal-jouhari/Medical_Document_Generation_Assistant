"""Erreurs métier à message sûr (N-11). Le code est stable ; aucun détail technique."""


class SafeError(Exception):
    """Erreur dont le code seul est exposé au client."""

    code = "error"

    def __init__(self) -> None:
        super().__init__(self.code)


class AuthenticationRequired(SafeError):
    code = "authentication_required"


class InvalidSession(SafeError):
    code = "session_invalid"


class MfaRequired(SafeError):
    code = "mfa_required"


class IdentityProviderUnavailable(SafeError):
    code = "identity_provider_unavailable"


class Forbidden(SafeError):
    code = "forbidden"


class NotFound(SafeError):
    """Ressource inexistante OU non autorisée : réponse identique (F-25)."""

    code = "not_found"
