import logging.handlers
from pathlib import Path

from app.core.logging import configure_logging


def test_N10_logs_rotate_daily_and_keep_30_days(tmp_path: Path) -> None:
    configure_logging(str(tmp_path / "logs"), 30)
    handlers = [
        h
        for h in logging.getLogger().handlers
        if isinstance(h, logging.handlers.TimedRotatingFileHandler)
    ]
    assert len(handlers) == 1
    assert handlers[0].backupCount == 30
    assert handlers[0].when == "MIDNIGHT"
    assert handlers[0].utc is True
