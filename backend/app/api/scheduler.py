"""Ordonnanceur de purge (N-10) : une passe au démarrage, puis à intervalle régulier.

Les consultations expirées sont effacées avec le rôle applicatif ; l'audit de plus d'un an avec
le rôle de purge, seul autorisé à le supprimer (ADR 0006, ADR 0021). Aucune donnée patient
n'est journalisée : seulement les nombres d'éléments purgés.
"""

import asyncio
from contextlib import suppress

import structlog
from sqlalchemy.orm import Session

from app.adapters.db import make_engine
from app.adapters.storage import LocalFileStore
from app.api.deps import session_factory
from app.core.config import Settings
from app.domain.clock import Clock
from app.services.retention import RetentionPolicy, RetentionService

log = structlog.get_logger()


def run_retention(settings: Settings, clock: Clock) -> None:
    policy = RetentionPolicy(settings.retention_consultation_days, settings.retention_audit_days)
    with session_factory()() as session:
        service = RetentionService(session, clock, LocalFileStore(settings.storage_dir), policy)
        consultations = service.purge_consultations()
        session.commit()
    audit_events = 0
    if settings.purge_database_url is not None:
        engine = make_engine(settings.purge_database_url.get_secret_value())
        try:
            with Session(engine) as purge_session:
                audit_events = service.purge_audit(purge_session)
                purge_session.commit()
        finally:
            engine.dispose()
    else:
        log.warning("retention_audit_purge_not_configured")
    log.info("retention_purged", consultations=consultations, audit_events=audit_events)


async def retention_loop(settings: Settings, clock: Clock) -> None:
    while True:
        try:
            await asyncio.to_thread(run_retention, settings, clock)
        except Exception as error:  # la purge suivante est retentée ; aucun détail journalisé
            log.error("retention_failed", error_type=type(error).__name__)
        await asyncio.sleep(settings.retention_interval_hours * 3600)


async def stop(task: "asyncio.Task[None]") -> None:
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
