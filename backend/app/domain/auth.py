"""Rôles et permissions (F-02). Ajouter un rôle = une entrée ici, sans toucher aux routes."""

from enum import StrEnum


class Role(StrEnum):
    CLINICIAN = "clinician"


class Permission(StrEnum):
    USE_DOCUMENTS = "documents:use"


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    Role.CLINICIAN.value: frozenset({Permission.USE_DOCUMENTS}),
}


def permissions_of(roles: tuple[str, ...]) -> frozenset[Permission]:
    granted: set[Permission] = set()
    for name in roles:
        granted |= ROLE_PERMISSIONS.get(name, frozenset())
    return frozenset(granted)
