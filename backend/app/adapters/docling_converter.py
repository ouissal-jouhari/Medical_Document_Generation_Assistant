"""Docling sur CPU. Importé à la demande : le paquet est optionnel (extra « ocr »).

Les poids des modèles sont embarqués dans l'image Docker (DOCLING_ARTIFACTS_PATH) : aucun
téléchargement à l'exécution, compatible on-premise (JALONS, tâche 2).
"""

import io
from typing import Any


class DoclingMarkdownConverter:
    def __init__(self, artifacts_path: str | None = None) -> None:
        self._artifacts_path = artifacts_path
        self._converter: Any = None

    def _get_converter(self) -> Any:
        if self._converter is None:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import (
                DocumentConverter,
                ImageFormatOption,
                PdfFormatOption,
            )

            options = PdfPipelineOptions(
                artifacts_path=self._artifacts_path, do_ocr=True, do_table_structure=True
            )
            self._converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=options),
                    InputFormat.IMAGE: ImageFormatOption(pipeline_options=options),
                }
            )
        return self._converter

    def convert_to_markdown(self, content: bytes, suffix: str) -> str:
        from docling.datamodel.base_models import DocumentStream

        # Nom fixe : le nom d'origine du fichier n'est jamais transmis (donnée possible).
        stream = DocumentStream(name=f"superbill.{suffix}", stream=io.BytesIO(content))
        result = self._get_converter().convert(stream)
        return str(result.document.export_to_markdown())
