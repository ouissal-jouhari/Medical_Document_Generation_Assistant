"""Table ICD-10-CM du CDC (FY2026), versionnée dans app/data (P9)."""

from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "icd10cm_fy2026_codes.txt"


def load_known_icd() -> frozenset[str]:
    """Codes sans point. Un code absent donne un avertissement non bloquant."""
    lines = DATA_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(line.strip() for line in lines if line.strip() and not line.startswith("#"))
