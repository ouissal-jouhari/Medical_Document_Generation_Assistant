"""Accès base de données (SQLAlchemy). Les entités arrivent avec les jalons suivants."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)
