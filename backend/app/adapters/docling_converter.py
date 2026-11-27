"""Docling sur CPU. Importé à la demande : le paquet est optionnel (extra « ocr »).

Les poids des modèles sont embarqués dans l'image Docker (DOCLING_ARTIFACTS_PATH) : aucun
téléchargement à l'exécution, compatible on-premise (JALONS, tâche 2).
"""

import io
from typing import Any


def _otsu_threshold(histogram: list[int]) -> int:
    total = sum(histogram)
    weighted_total = sum(level * count for level, count in enumerate(histogram))
    background = 0
    background_sum = 0
    best_level, best_variance = 128, -1.0
    for level, count in enumerate(histogram):
        background += count
        if background == 0:
            continue
        foreground = total - background
        if foreground == 0:
            break
        background_sum += level * count
        mean_back = background_sum / background
        mean_fore = (weighted_total - background_sum) / foreground
        variance = background * foreground * (mean_back - mean_fore) ** 2
        if variance > best_variance:
            best_level, best_variance = level, variance
    return best_level


def preprocess_image(content: bytes) -> bytes:
    """Nettoie un scan avant l'OCR : niveaux de gris, contraste, débruitage, binarisation (Otsu),
    agrandissement des petites images. Améliore nettement la lecture des champs (Tesseract)."""
    from PIL import Image, ImageFilter, ImageOps

    with Image.open(io.BytesIO(content)) as source:
        image = ImageOps.exif_transpose(source).convert("L")
    if image.width < 1600:
        factor = 1600 / image.width
        image = image.resize((1600, round(image.height * factor)), Image.Resampling.LANCZOS)
    image = ImageOps.autocontrast(image, cutoff=2).filter(ImageFilter.MedianFilter(3))
    threshold = _otsu_threshold(image.histogram())
    image = image.point(lambda value: 255 if value > threshold else 0)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class DoclingMarkdownConverter:
    def __init__(self, artifacts_path: str | None = None) -> None:
        self._artifacts_path = artifacts_path
        self._converter: Any = None

    def _get_converter(self) -> Any:
        if self._converter is None:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import (
                PdfPipelineOptions,
                TesseractCliOcrOptions,
            )
            from docling.document_converter import (
                DocumentConverter,
                ImageFormatOption,
                PdfFormatOption,
            )

            options = PdfPipelineOptions(
                artifacts_path=self._artifacts_path,
                do_ocr=True,
                do_table_structure=True,
                ocr_options=TesseractCliOcrOptions(lang=["eng"]),
            )
            self._converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=options),
                    InputFormat.IMAGE: ImageFormatOption(pipeline_options=options),
                }
            )
        return self._converter

    @staticmethod
    def _ocr_image(content: bytes) -> str:
        """Image : Tesseract direct sur l'image nettoyée (psm 6, lecture ligne par ligne).
        La mise en page de Docling mélange l'ordre des champs d'un formulaire (ADR 0012)."""
        import subprocess  # noqa: S404  # nosec B404

        completed = subprocess.run(  # noqa: S603  # nosec B603 B607
            ["tesseract", "stdin", "stdout", "-l", "eng", "--psm", "6"],  # noqa: S607
            input=preprocess_image(content),
            capture_output=True,
            check=True,
            timeout=120,
        )
        return completed.stdout.decode("utf-8", errors="replace")

    def convert_to_markdown(self, content: bytes, suffix: str) -> str:
        from docling.datamodel.base_models import DocumentStream

        if suffix != "pdf":
            return self._ocr_image(content)
        # Nom fixe : le nom d'origine du fichier n'est jamais transmis (donnée possible).
        stream = DocumentStream(name=f"superbill.{suffix}", stream=io.BytesIO(content))
        result = self._get_converter().convert(stream)
        return str(result.document.export_to_markdown())
