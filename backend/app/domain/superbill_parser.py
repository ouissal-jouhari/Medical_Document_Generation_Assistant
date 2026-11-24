"""Parsing déterministe d'une Superbill (sans LLM) : texte extrait -> SuperbillData.

Aucun LLM n'intervient dans l'extraction (diagrammes) et le nom du patient ne sort jamais du
système (N-19). Un seul gabarit de Superbill est géré (L-01) : champs repérés par leur libellé,
codes ICD-10-CM et CPT repérés dans leurs sections. Le clinicien vérifie le résultat (R-02).
"""

import re
from datetime import date

from app.domain.superbill import (
    CPT,
    ICD10CM,
    Diagnosis,
    Procedure,
    SuperbillData,
)

# (champ, motif, souple). Après le libellé : deux-points, tabulation ou deux espaces au moins.
# Un libellé « souple » accepte aussi un seul espace suivi d'une majuscule, d'un chiffre, de « $ »
# ou de « ( » (cellule d'un formulaire sans deux-points), ou la fin de ligne (valeur à la ligne
# suivante). Les mots courts et ambigus restent stricts. L'ordre compte : le premier motif qui
# correspond l'emporte, donc les libellés ignorés et les plus spécifiques passent en premier
# (« physician npi » avant « physician »).
_LABELS: list[tuple[str, str, bool]] = [
    # Libellés connus mais non utilisés : ils servent seulement à terminer la valeur précédente.
    ("ignored", r"(?:physician\s+)?signature", False),
    ("ignored", r"physician\s+npi", True),
    ("ignored", r"(?:primary|secondary)\s+insurance", True),
    ("ignored", r"insurance\s+(?:provider|company|carrier|name|id)", True),
    ("ignored", r"insurance", False),
    ("ignored", r"payer", False),
    ("ignored", r"superbill\s+(?:no\.?|number|#)", True),
    ("ignored", r"date\s+issued", True),
    ("ignored", r"(?:policy|group|member)\s+(?:id|number|no\.?|#)", True),
    ("ignored", r"copay(?:\s+received)?", True),
    ("ignored", r"balance(?:\s+due)?", True),
    ("ignored", r"phone(?:\s+(?:number|no\.?))?", True),
    ("ignored", r"tel(?:ephone)?", True),
    ("ignored", r"fax", True),
    ("ignored", r"address", True),
    ("ignored", r"e-?mail", False),
    ("ignored", r"npi", True),
    ("ignored", r"tax\s+id", True),
    ("ignored", r"(?:sex|gender)", True),
    ("patient_full_name", r"patient\s+name", True),
    ("patient_full_name", r"name\s+of\s+patient", True),
    ("patient_full_name", r"patient", False),
    ("patient_date_of_birth", r"date\s+of\s+birth", True),
    ("patient_date_of_birth", r"birth\s+date", True),
    ("patient_date_of_birth", r"dob", True),
    ("patient_id", r"patient\s+id", True),
    ("patient_id", r"patient\s*#", True),
    ("patient_id", r"mrn", True),
    ("patient_id", r"medical\s+record\s+(?:number|no\.?|#)", True),
    ("patient_id", r"account\s+(?:number|no\.?|#)", True),
    ("physician_name", r"rendering\s+provider", True),
    ("physician_name", r"referring\s+physician", True),
    ("physician_name", r"physician(?:\s+name)?", True),
    ("physician_name", r"provider(?:\s+name)?", False),
    ("physician_name", r"doctor", False),
    ("date_of_service", r"date\s+of\s+service", True),
    ("date_of_service", r"service\s+date", True),
    ("date_of_service", r"dos", False),
    ("place_of_service", r"place\s+of\s+service", True),
    ("place_of_service", r"pos", False),
    ("total_charges", r"total\s+(?:charges?|fees?|amount)", True),
    ("total_charges", r"grand\s+total", True),
]
_SEP_STRICT = r"(?:\s*[:：]\s*|\s{2,}|\t+)"
_SEP_LOOSE = r"(?:\s*[:：]\s*|\s{2,}|\t+|\s(?=(?-i:[A-Z0-9$(]))|\s*$)"


def _build_label_regex() -> tuple[re.Pattern[str], dict[str, str]]:
    names: dict[str, str] = {}
    alternatives = []
    for index, (fld, pattern, loose) in enumerate(_LABELS):
        group = f"l{index}"
        names[group] = fld
        sep = _SEP_LOOSE if loose else _SEP_STRICT
        alternatives.append(f"(?P<{group}>{pattern}){sep}")
    regex = re.compile(r"(?<![\w])(?:" + "|".join(alternatives) + r")", re.IGNORECASE)
    return regex, names


_LABEL_RE, _GROUP_FIELD = _build_label_regex()

_DIAG_HEADING = re.compile(
    r"^\s*(?:diagnos[ie]s|diagnosis\s+codes?|icd[- ]?10(?:[- ]?cm)?(?:\s+codes?)?)\b", re.I
)
_PROC_HEADING = re.compile(
    r"^\s*(?:procedures?|procedure\s+codes?|cpt(?:\s+codes?)?|services?(?:\s+rendered)?)\b", re.I
)
_SECTION_END = re.compile(
    r"^\s*(?:total|billing|insurance|payer|signature|clinic|notes?|remarks|balance)\b", re.I
)
_MONEY = re.compile(r"^\$?\d[\d,]*\.\d{2}$")
_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ]
    )
}


def normalize_date(raw: str) -> str:
    """Convertit une date lue (US : MM/DD/YYYY) en ISO ; sinon renvoie le texte tel quel."""
    text = raw.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if match:
        month, day, year = (int(g) for g in match.groups())
    else:
        match = re.fullmatch(r"([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})", text)
        if not match or match.group(1).lower() not in _MONTHS:
            return text
        month, day, year = _MONTHS[match.group(1).lower()], int(match.group(2)), int(match.group(3))
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return text


def _clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or re.fullmatch(r"[\s|:\-–—=_*#]+", line):
            continue
        if "|" in line:  # tableau Markdown de Docling : cellules séparées par deux espaces
            line = "  ".join(cell.strip() for cell in line.strip("|").split("|") if cell.strip())
        line = re.sub(r"^[#*\s]+|[*\s]+$", "", line)
        if line:
            lines.append(line)
    return lines


def _extract_fields(lines: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    pending: str | None = None  # libellé seul en fin de ligne : la valeur est sur la ligne suivante
    for line in lines:
        if pending is not None:
            if not _LABEL_RE.match(line):
                found.setdefault(pending, line.strip())
            pending = None
        matches = list(_LABEL_RE.finditer(line))
        for i, match in enumerate(matches):
            group = next(name for name, value in match.groupdict().items() if value is not None)
            fld = _GROUP_FIELD[group]
            end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
            value = line[match.end() : end].strip(" \t:-–")
            if value:
                found.setdefault(fld, value)
            elif i + 1 == len(matches):
                pending = fld
    return found


def _section(lines: list[str], heading: re.Pattern[str], other: re.Pattern[str]) -> list[str]:
    for start, line in enumerate(lines):
        if heading.match(line) and not _LABEL_RE.match(line):
            body: list[str] = []
            for follower in lines[start + 1 :]:
                if other.match(follower) or _SECTION_END.match(follower):
                    break
                if _LABEL_RE.match(follower):
                    break
                body.append(follower)
            return [line, *body]
    return []


def _looks_like_code(token: str) -> bool:
    return bool(ICD10CM.match(token.upper()) or CPT.match(token.upper()))


def _split_code(row: str) -> tuple[str, str] | None:
    tokens = row.split()
    if (
        len(tokens) >= 2
        and re.fullmatch(r"(?:\d{1,2}|[A-Za-z])[.)]?", tokens[0])
        and _looks_like_code(tokens[1].strip(",;"))
    ):
        tokens = tokens[1:]  # référence ou numéro de ligne (« A », « 1 »)
    if not tokens:
        return None
    return tokens[0].strip(",;"), " ".join(tokens[1:]).strip(" -–:")


def _parse_diagnoses(section: list[str]) -> tuple[Diagnosis, ...]:
    rows = []
    for row in section[1:]:
        split = _split_code(row)
        if split and ICD10CM.match(split[0].upper()):
            rows.append(Diagnosis(split[0].upper(), split[1]))
    return tuple(rows)


def _parse_procedures(section: list[str]) -> tuple[Procedure, ...]:
    if not section:
        return ()
    header = " ".join(row for row in section[:3] if not _split_is_code(row))
    has_units_column = bool(re.search(r"\b(?:units?|qty|quantity)\b", header, re.I))
    has_dx_column = bool(re.search(r"\bdx\b|diagnos\w*\s+(?:ref|pointer)|\bpointer", header, re.I))
    rows = []
    for row in section[1:]:
        split = _split_code(row)
        if not split or not CPT.match(split[0].upper()):
            continue
        tokens = split[1].split()
        while tokens and _MONEY.match(tokens[-1]):
            tokens.pop()
        units = None
        if has_units_column and tokens and re.fullmatch(r"\d{1,3}", tokens[-1]):
            units = int(tokens.pop())
        if has_dx_column and tokens and re.fullmatch(r"[A-L],?", tokens[-1]):
            # Références de diagnostic (« A, B ») : la dernière, puis les « X, » qui la précèdent.
            tokens.pop()
            while tokens and re.fullmatch(r"[A-L],", tokens[-1]):
                tokens.pop()
        rows.append(Procedure(split[0].upper(), " ".join(tokens).strip(" -–:"), units))
    return tuple(rows)


def _split_is_code(row: str) -> bool:
    split = _split_code(row)
    return bool(split and (CPT.match(split[0].upper()) or ICD10CM.match(split[0].upper())))


def parse_superbill_text(text: str, page_count: int) -> SuperbillData:
    lines = _clean_lines(text)
    fields = _extract_fields(lines)
    diagnoses = _parse_diagnoses(_section(lines, _DIAG_HEADING, _PROC_HEADING))
    procedures = _parse_procedures(_section(lines, _PROC_HEADING, _DIAG_HEADING))
    dob = fields.get("patient_date_of_birth")
    dos = fields.get("date_of_service")
    return SuperbillData(
        patient_full_name=fields.get("patient_full_name"),
        patient_date_of_birth=normalize_date(dob) if dob else None,
        patient_id=fields.get("patient_id"),
        physician_name=fields.get("physician_name"),
        date_of_service=normalize_date(dos) if dos else None,
        place_of_service=fields.get("place_of_service"),
        diagnoses=diagnoses,
        procedures=procedures,
        total_charges=fields.get("total_charges"),
        page_count=page_count,
    )
