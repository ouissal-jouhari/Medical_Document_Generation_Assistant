"""F-12 : le délai du proxy couvre le plus long traitement serveur (extraction ou génération)."""

import re
from pathlib import Path

from app.core.config import Settings

CADDYFILE = Path(__file__).resolve().parents[2] / "deploy" / "Caddyfile"


def test_F12_proxy_response_timeout_covers_server_budgets() -> None:
    match = re.search(r"response_header_timeout\s+(\d+)s", CADDYFILE.read_text(encoding="utf-8"))
    assert match is not None, "délai de réponse du proxy non défini dans deploy/Caddyfile"
    settings = Settings()
    longest = max(settings.extraction_timeout_seconds, settings.llm_total_timeout_seconds)
    assert int(match.group(1)) >= longest + 30
