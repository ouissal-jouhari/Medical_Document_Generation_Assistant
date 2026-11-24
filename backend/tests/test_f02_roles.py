"""F-02 : chaque route vérifie l'authentification et le rôle.

Ajouter un rôle ne demande pas de modifier les routes.
"""

import pytest

from app.api.deps import get_current_user
from app.domain.auth import ROLE_PERMISSIONS, Permission
from tests.conftest import Api
from tests.helpers_routes import api_routes, route_depends_on

# Routes publiques volontaires : sonde de santé uniquement.
PUBLIC_ROUTES = {"/health"}


def test_F02_every_route_declares_the_authentication_dependency(api: Api) -> None:
    routes = api_routes(api.app)
    paths = {route.path for route, _ in routes}
    assert {"/health", "/me"} <= paths  # le parcours n'est pas vide
    for route, inherited in routes:
        if route.path in PUBLIC_ROUTES:
            continue
        assert route_depends_on(route, inherited, get_current_user), route.path


def test_F02_unauthenticated_call_to_every_protected_route_is_refused(api: Api) -> None:
    checked = 0
    for route, _ in api_routes(api.app):
        if route.path in PUBLIC_ROUTES:
            continue
        for method in route.methods or set():
            response = api.client.request(method, route.path)
            assert response.status_code in (401, 422), (method, route.path)
            checked += 1
    assert checked >= 1


def test_F02_adding_a_role_requires_no_route_change(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    denied = api.client.get("/me", headers=api.headers(roles=("auditeur",)))
    assert denied.status_code == 403
    monkeypatch.setitem(ROLE_PERMISSIONS, "auditeur", frozenset({Permission.USE_DOCUMENTS}))
    allowed = api.client.get("/me", headers=api.headers(roles=("auditeur",)))
    assert allowed.status_code == 200
