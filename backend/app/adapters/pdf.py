"""Export PDF (F-18, F-23, F-24) : Jinja2 avec autoéchappement, WeasyPrint sans accès externe.

Le contenu des sections est échappé (N-06) ; le chargeur d'URL refuse toute ressource : aucune
lecture de fichier ni requête réseau depuis le contenu. En-tête et pied de page sont des
éléments courants répétés sur chaque page, avec la pagination « x / y » (P15).
WeasyPrint est importé au premier rendu : ses bibliothèques système (Pango) ne sont chargées
que par l'export.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.domain.errors import ExportError
from app.domain.values import ExportableDocument, ExportedFile, ProvenanceReport

PDF_MEDIA_TYPE = "application/pdf"
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "pdf"

# Les avertissements de WeasyPrint peuvent citer une URL issue du contenu : jamais journalisés.
logging.getLogger("weasyprint").setLevel(logging.CRITICAL)
logging.getLogger("fontTools").setLevel(logging.CRITICAL)


def blocking_url_fetcher(on_request: Callable[[str], None] | None = None) -> Any:
    """Chargeur d'URL qui refuse toute ressource (fichier local, réseau, données)."""
    from weasyprint.urls import URLFetcher, URLFetchingError

    class BlockingUrlFetcher(URLFetcher):  # type: ignore[misc]
        def fetch(self, url: str, headers: object = None) -> Any:
            if on_request is not None:
                on_request(url)
            raise URLFetchingError("blocked")

    return BlockingUrlFetcher()


def render_pdf(html: str, on_request: Callable[[str], None] | None = None) -> bytes:
    try:
        from weasyprint import HTML

        pdf: bytes = HTML(
            string=html, base_url=None, url_fetcher=blocking_url_fetcher(on_request)
        ).write_pdf()
    except Exception as error:  # détail technique jamais propagé (N-11)
        raise ExportError from error
    return pdf


class WeasyPrintExporter:
    def __init__(self, template_dir: Path = TEMPLATE_DIR) -> None:
        self._env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(enabled_extensions=("html", "j2"), default=True),
        )

    def html(self, document: ExportableDocument) -> str:
        return self._env.get_template("document.html.j2").render(doc=document)

    def export(self, document: ExportableDocument, filename: str) -> ExportedFile:
        return ExportedFile(filename, PDF_MEDIA_TYPE, render_pdf(self.html(document)))

    def export_provenance(self, report: ProvenanceReport, filename: str) -> ExportedFile:
        html = self._env.get_template("provenance.html.j2").render(report=report)
        return ExportedFile(filename, PDF_MEDIA_TYPE, render_pdf(html))
