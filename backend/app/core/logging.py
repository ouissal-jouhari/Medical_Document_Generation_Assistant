"""structlog : JSON, UTC, sans donnée patient (N-08), rotation à 30 jours (N-10)."""

import logging
import logging.handlers
from pathlib import Path

import structlog
from structlog.typing import EventDict, WrappedLogger

# Clés qui pourraient porter une donnée patient ou un secret : jamais journalisées.
FORBIDDEN_KEYS = frozenset(
    {
        "text",
        "content",
        "body",
        "input",
        "prompt",
        "transcript",
        "patient",
        "patient_name",
        "name",
        "password",
        "token",
        "secret",
        "authorization",
        "api_key",
        "query",
        "ctx",
    }
)


def drop_sensitive_keys(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    for key in FORBIDDEN_KEYS & event_dict.keys():
        event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging(log_dir: str, retention_days: int = 30) -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        Path(log_dir) / "xeleron.log",
        when="midnight",
        backupCount=retention_days,
        utc=True,
        encoding="utf-8",
    )
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    root.addHandler(file_handler)
    root.addHandler(logging.StreamHandler())
    root.setLevel(logging.INFO)
    # Le journal d'accès d'uvicorn contient les URL complètes : remplacé par notre middleware.
    logging.getLogger("uvicorn.access").disabled = True
    # Les clients HTTP journalisent l'URL complète (clé d'API possible) : niveau WARNING seulement.
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            drop_sensitive_keys,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
