"""F-02 : chaque route vérifie l'authentification et le rôle ; ajouter un rôle ne touche pas aux routes."""  # noqa: E501

from collections.abc import Iterator

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.api.deps import get_current_user
from app.domain.auth import ROLE_PERMISSIONS, Permission
from tests.conftest import Api

# Routes publiques volontaires : sonde de santé uniquement.
PUBLIC_ROUTES = {"/health"}


def _dependencies(dependant: Dependant) -> Iterator[object]:
    for sub in dependant.dependencies:
        yield sub.call
        yield from _dependencies(sub)


def test_F02_every_route_declares_the_authentication_dependency(api: Api) -> None:
    protected = []
    for route in api.app.routes:
        if not isinstance(route, APIRoute) or route.path in PUBLIC_ROUTES:
            continue
        assert get_current_user in set(_dependencies(route.dependant)), route.path
        protected.append(route.path)
    assert "/me" in protected


def test_F02_unauthenticated_call_to_every_protected_route_is_refused(api: Api) -> None:
    for route in api.app.routes:
        if isinstance(route, APIRoute) and route.path not in PUBLIC_ROUTES:
            for method in route.methods:
                response = api.client.request(method, route.path.replace("{", "").replace("}", ""))
                assert response.status_code in (401, 404, 405, 422), (method, route.path)
                assert response.status_code != 200


def test_F02_adding_a_role_requires_no_route_change(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    denied = api.client.get("/me", headers=api.headers(roles=("auditeur",)))
    assert denied.status_code == 403
    monkeypatch.setitem(ROLE_PERMISSIONS, "auditeur", frozenset({Permission.USE_DOCUMENTS}))
    allowed = api.client.get("/me", headers=api.headers(roles=("auditeur",)))
    assert allowed.status_code == 200
