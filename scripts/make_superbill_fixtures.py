"""Génère les Superbills synthétiques de test (données fictives uniquement, C-03).

Sorties dans backend/tests/fixtures/superbills/ :
- clean_superbill.pdf : cas propre (couche texte), avec clean_superbill.expected.json ;
- degraded_scan.png : même contenu en image dégradée (passe par Docling), avec son .expected.json ;
- invalid_renamed.pdf : fichier texte renommé en .pdf (cas invalide, refusé par N-06).

À lancer depuis backend/ : uv run python ../scripts/make_superbill_fixtures.py
"""

import json
import random
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parents[1] / "backend" / "tests" / "fixtures" / "superbills"

LEFT = [
    ("Patient Name: Jane Doe", "Date of Birth: 04/12/1980"),
    ("Patient ID: P-000123", "Insurance Provider: Northwind Health"),
    ("Physician: Dr. Alice Martin", "Date of Service: 11/20/2026"),
    ("Place of Service: Office", ""),
]
DIAGNOSES = [
    ("E11.9", "Type 2 diabetes mellitus without complications"),
    ("I10", "Essential (primary) hypertension"),
]
PROCEDURES = [
    ("99213", "Office visit, established patient", "1", "$150.00"),
    ("36415", "Collection of venous blood by venipuncture", "1", "$12.00"),
]
TOTAL = "Total Charges: $162.00"

EXPECTED = {
    "patient": {"fullName": "Jane Doe", "dateOfBirth": "1980-04-12", "patientId": "P-000123"},
    "physician": {"name": "Dr. Alice Martin"},
    "encounter": {"dateOfService": "2026-11-20", "placeOfService": "Office"},
    "diagnoses": [{"code": c, "description": d} for c, d in DIAGNOSES],
    "procedures": [{"code": c, "description": d, "units": int(u)} for c, d, u, _ in PROCEDURES],
    "billing": {"totalCharges": "$162.00"},
}


def make_pdf(path: Path) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Northwind Family Clinic - SUPERBILL", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    for left, right in LEFT:
        pdf.cell(95, 7, left)
        pdf.cell(95, 7, right, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Diagnoses", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(35, 7, "ICD-10 Code")
    pdf.cell(0, 7, "Description", new_x="LMARGIN", new_y="NEXT")
    for code, description in DIAGNOSES:
        pdf.cell(35, 7, code)
        pdf.cell(0, 7, description, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Procedures", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    for header, width in (("CPT Code", 30), ("Description", 100), ("Units", 20), ("Charge", 30)):
        pdf.cell(width, 7, header)
    pdf.ln(7)
    for code, description, units, charge in PROCEDURES:
        for value, width in ((code, 30), (description, 100), (units, 20), (charge, 30)):
            pdf.cell(width, 7, value)
        pdf.ln(7)
    pdf.ln(4)
    pdf.cell(0, 8, TOTAL, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))


def make_degraded_scan(path: Path) -> None:
    rng = random.Random(7)  # noqa: S311 - bruit d'image reproductible, sans usage cryptographique
    image = Image.new("L", (1700, 2200), 255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=34)
    bold = ImageFont.load_default(size=44)
    y = 120
    draw.text((120, y), "Northwind Family Clinic - SUPERBILL", font=bold, fill=0)
    y += 110
    for left, right in LEFT:
        draw.text((120, y), left, font=font, fill=0)
        draw.text((900, y), right, font=font, fill=0)
        y += 62
    y += 40
    draw.text((120, y), "Diagnoses", font=bold, fill=0)
    y += 70
    draw.text((120, y), "ICD-10 Code", font=font, fill=0)
    draw.text((420, y), "Description", font=font, fill=0)
    y += 58
    for code, description in DIAGNOSES:
        draw.text((120, y), code, font=font, fill=0)
        draw.text((420, y), description, font=font, fill=0)
        y += 58
    y += 40
    draw.text((120, y), "Procedures", font=bold, fill=0)
    y += 70
    for header, x in (("CPT Code", 120), ("Description", 420), ("Units", 1200), ("Charge", 1400)):
        draw.text((x, y), header, font=font, fill=0)
    y += 58
    for code, description, units, charge in PROCEDURES:
        for value, x in ((code, 120), (description, 420), (units, 1200), (charge, 1400)):
            draw.text((x, y), value, font=font, fill=0)
        y += 58
    y += 40
    draw.text((120, y), TOTAL, font=font, fill=0)
    # Dégradation : légère rotation, flou, bruit.
    image = image.rotate(1.2, resample=Image.Resampling.BICUBIC, fillcolor=255)
    image = image.filter(ImageFilter.GaussianBlur(1.1))
    noisy = image.load()
    if noisy is None:
        raise SystemExit("image illisible")
    for _ in range(60000):
        x, y = rng.randrange(image.width), rng.randrange(image.height)
        noisy[x, y] = rng.choice((0, 90, 160))
    image.save(path, format="PNG")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    make_pdf(OUT / "clean_superbill.pdf")
    make_degraded_scan(OUT / "degraded_scan.png")
    for name in ("clean_superbill", "degraded_scan"):
        expected = {**EXPECTED, "extraction": {"pageCount": 1}}
        (OUT / f"{name}.expected.json").write_text(
            json.dumps(expected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    (OUT / "invalid_renamed.pdf").write_text(
        "Ceci n'est pas un PDF : fichier texte renommé en .pdf (cas invalide synthétique).\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
