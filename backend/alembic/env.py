from alembic import context
from app.adapters.db import Base, make_engine
from app.core.config import get_settings

target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = make_engine(get_settings().database_url.get_secret_value())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
