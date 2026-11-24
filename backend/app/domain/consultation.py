"""États d'une consultation (niveau 1 du workflow, SRS section 3)."""

from enum import StrEnum


class ConsultationState(StrEnum):
    UPLOADED = "uploaded"
    PARSED = "parsed"
    VALIDATED = "validated"
