"""Couche d'accès filtrée par auteur (F-25).

Aucune méthode ne lit une ressource sans `author_id` : l'isolement est garanti par construction.
Une ressource inexistante et une ressource d'un autre auteur sont indiscernables (None).
"""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, Session

T = TypeVar("T", bound=DeclarativeBase)


class AuthorScopedRepository(Generic[T]):  # noqa: UP046 - compatibilité mypy strict
    """Le modèle doit avoir les colonnes `id` et `author_id`."""

    def __init__(self, session: Session, model: type[T]) -> None:
        self._session = session
        self._model: Any = model

    def get(self, resource_id: UUID, author_id: UUID) -> T | None:
        statement = select(self._model).where(
            self._model.id == resource_id, self._model.author_id == author_id
        )
        result: T | None = self._session.scalars(statement).first()
        return result

    def list(self, author_id: UUID) -> Sequence[T]:
        statement = select(self._model).where(self._model.author_id == author_id)
        return self._session.scalars(statement).all()

    def add(self, entity: T) -> T:
        self._session.add(entity)
        self._session.flush()
        return entity
