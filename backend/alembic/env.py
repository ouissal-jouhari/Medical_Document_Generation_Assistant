from alembic import context
from app.adapters import models  # noqa: F401  (enregistre les tables)
from app.adapters.db import Base, make_engine
from app.core.config import get_settings

target_metadata = Base.metadata


def run_migrations_online() -> None:
    settings = get_settings()
    url = settings.migration_database_url or settings.database_url
    engine = make_engine(url.get_secret_value())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
