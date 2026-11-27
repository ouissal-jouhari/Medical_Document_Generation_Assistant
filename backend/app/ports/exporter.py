from typing import Protocol

from app.domain.values import ExportableDocument, ExportedFile, ProvenanceReport


class DocumentExporter(Protocol):
    """Export d'un document approuvé (PDF au MVP ; port prévu pour un export FHIR futur).

    Un échec de rendu lève `ExportError`, sans détail : le service renvoie un message sûr.
    """

    def export(self, document: ExportableDocument, filename: str) -> ExportedFile: ...

    def export_provenance(self, report: ProvenanceReport, filename: str) -> ExportedFile: ...
