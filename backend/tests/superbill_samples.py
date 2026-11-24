"""Textes d'extraction synthétiques (données fictives) et petits fichiers de test."""

import io
from typing import Any

from fpdf import FPDF
from PIL import Image
from pypdf import PdfWriter

# Sortie typique d'une couche texte PDF : une ligne par rangée, cellules séparées par un espace.
CLEAN_TEXT = """Northwind Family Clinic - SUPERBILL
Patient Name: Jane Doe Date of Birth: 04/12/1980
Patient ID: P-000123 Insurance Provider: Northwind Health
Physician: Dr. Alice Martin Date of Service: 11/20/2026
Place of Service: Office
Diagnoses
ICD-10 Code Description
E11.9 Type 2 diabetes mellitus without complications
I10 Essential (primary) hypertension
Procedures
CPT Code Description Units Charge
99213 Office visit, established patient 1 $150.00
36415 Collection of venous blood by venipuncture 1 $12.00
Total Charges: $162.00
"""

# Sortie typique de Docling : tableaux Markdown, libellés dans des cellules sans deux-points.
MARKDOWN_TEXT = """## Northwind Family Clinic - SUPERBILL

| Patient Name | Jane Doe |
|---|---|
| Date of Birth | April 12, 1980 |
| Patient ID | P-000123 |
| Physician | Dr. Alice Martin |
| Date of Service | 2026-11-20 |

## Diagnoses

| ICD-10 Code | Description |
|---|---|
| E11.9 | Type 2 diabetes mellitus without complications |
| I10 | Essential (primary) hypertension |

## Procedures

| CPT Code | Description | Units | Charge |
|---|---|---|---|
| 99213 | Office visit, established patient | 1 | $150.00 |

Total Charges: $150.00
"""

EXPECTED_CLEAN: dict[str, Any] = {
    "patient": {"fullName": "Jane Doe", "dateOfBirth": "1980-04-12", "patientId": "P-000123"},
    "physician": {"name": "Dr. Alice Martin"},
    "encounter": {"dateOfService": "2026-11-20", "placeOfService": "Office"},
    "diagnoses": [
        {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications"},
        {"code": "I10", "description": "Essential (primary) hypertension"},
    ],
    "procedures": [
        {"code": "99213", "description": "Office visit, established patient", "units": 1},
        {
            "code": "36415",
            "description": "Collection of venous blood by venipuncture",
            "units": 1,
        },
    ],
    "billing": {"totalCharges": "$162.00"},
    "extraction": {"pageCount": 1},
}


def pdf_with_text(text: str, pages: int = 1) -> bytes:
    """PDF avec couche texte ; `pages` pages. Une ligne de `text` par ligne du document."""
    pdf = FPDF()
    for _ in range(pages):
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)
        for line in text.splitlines():
            pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def blank_pdf(pages: int = 1) -> bytes:
    """PDF sans couche texte (équivalent d'un scan)."""
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def encrypted_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret-de-test")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def image_bytes(fmt: str = "PNG", size: tuple[int, int] = (200, 100)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, format=fmt)
    return buffer.getvalue()
