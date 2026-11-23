from typing import Protocol

from app.domain.values import ExportableDocument, ExportedFile


class DocumentExporter(Protocol):
    """Export d'un document approuvé (PDF au MVP ; port prévu pour un export FHIR futur)."""

    def export(self, document: ExportableDocument) -> ExportedFile: ...
