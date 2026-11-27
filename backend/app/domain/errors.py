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


class LlmUnavailable(SafeError):
    code = "llm_unavailable"


class LlmTimeout(SafeError):
    code = "llm_timeout"


class MalformedGeneration(SafeError):
    code = "malformed_generation"


class DocumentApproved(SafeError):
    """Document approuvé : figé, aucune modification possible (F-17)."""

    code = "document_approved"


class VersionConflict(SafeError):
    """La version attendue n'est plus la version courante (édition concurrente, F-14)."""

    code = "version_conflict"


class ApprovalBlocked(SafeError):
    """Approbation impossible : `extra["missing"]` liste les éléments manquants (N-11)."""

    code = "approval_blocked"


class NotApproved(SafeError):
    """Export clinique possible après approbation seulement (F-18)."""

    code = "document_not_approved"


class ExportFailed(SafeError):
    """Rendu PDF en échec (N-11) : le document reste inchangé, aucun détail exposé."""

    code = "export_failed"


class ExportError(Exception):
    """Échec technique de rendu (interne). Le détail n'est jamais exposé ni journalisé."""
