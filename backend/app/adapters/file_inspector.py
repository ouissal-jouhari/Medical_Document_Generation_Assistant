"""Contrôle d'un fichier déposé (F-03, N-06) : type réel, taille, pages, images piégées.

Le type est déterminé par les premiers octets (magic bytes), jamais par l'extension seule.
Le nom de fichier d'origine n'est ni conservé ni journalisé : il peut contenir un nom de patient.
"""

import io
from dataclasses import dataclass
from typing import Literal

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.domain.errors import (
    CorruptFile,
    EncryptedPdf,
    FileTooLarge,
    ImageTooLarge,
    TooManyPages,
    UnsupportedFormat,
)

MAX_PAGES = 3
# Protection contre les images piégées : au-delà, la taille décompressée est refusée (~25 Mpx).
MAX_IMAGE_PIXELS = 25_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

Kind = Literal["pdf", "png", "jpeg"]
_EXTENSIONS: dict[str, Kind] = {"pdf": "pdf", "png": "png", "jpg": "jpeg", "jpeg": "jpeg"}
_CONTENT_TYPES: dict[Kind, str] = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpeg": "image/jpeg",
}


@dataclass(frozen=True)
class FileInfo:
    kind: Kind
    content_type: str
    pages: int


def _detect(content: bytes) -> Kind:
    if content.startswith(b"%PDF-"):
        return "pdf"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    raise UnsupportedFormat


def _inspect_pdf(content: bytes) -> int:
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise EncryptedPdf
        pages = len(reader.pages)
    except EncryptedPdf:
        raise
    except (PyPdfError, ValueError, OSError, KeyError, RecursionError) as exc:
        raise CorruptFile from exc
    if pages < 1:
        raise CorruptFile
    if pages > MAX_PAGES:
        raise TooManyPages
    return pages


def _inspect_image(content: bytes) -> None:
    try:
        with Image.open(io.BytesIO(content)) as image:
            width, height = image.size
            if width * height > MAX_IMAGE_PIXELS:
                raise ImageTooLarge
            image.verify()
    except ImageTooLarge:
        raise
    except Image.DecompressionBombError as exc:
        raise ImageTooLarge from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise CorruptFile from exc


def inspect_upload(content: bytes, extension: str, max_bytes: int) -> FileInfo:
    """Valide le fichier ou lève une SafeError ; aucune consultation n'est créée avant."""
    if len(content) > max_bytes:
        raise FileTooLarge
    declared = _EXTENSIONS.get(extension.lower().lstrip("."))
    if declared is None:
        raise UnsupportedFormat
    kind = _detect(content)
    if kind != declared:  # fichier renommé : le type réel ne correspond pas à l'extension
        raise UnsupportedFormat
    pages = _inspect_pdf(content) if kind == "pdf" else 1
    if kind != "pdf":
        _inspect_image(content)
    return FileInfo(kind=kind, content_type=_CONTENT_TYPES[kind], pages=pages)
