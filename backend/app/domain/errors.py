"""Erreurs métier à message sûr (N-11). Le code est stable ; aucun détail technique."""


class SafeError(Exception):
    """Erreur dont le code seul est exposé au client."""

    code = "error"

    def __init__(self, extra: dict[str, object] | None = None) -> None:
        super().__init__(self.code)
        self.extra = extra or {}


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


class UnsupportedFormat(SafeError):
    code = "unsupported_format"


class FileTooLarge(SafeError):
    code = "file_too_large"


class TooManyPages(SafeError):
    code = "too_many_pages"


class EncryptedPdf(SafeError):
    code = "encrypted_pdf"


class CorruptFile(SafeError):
    code = "corrupt_file"


class ImageTooLarge(SafeError):
    code = "image_too_large"


class WrongState(SafeError):
    """Action impossible dans l'état actuel de la consultation."""

    code = "wrong_state"


class ValidationFailed(SafeError):
    """Données incomplètes ou invalides : `extra["issues"]` liste champ et code, sans valeur."""

    code = "validation_failed"


class ExtractionError(Exception):
    """Échec technique d'extraction (interne). Le détail n'est jamais exposé ni journalisé."""
