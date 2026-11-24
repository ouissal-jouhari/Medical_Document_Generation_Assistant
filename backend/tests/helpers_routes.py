"""Parcours de toutes les routes d'API, y compris celles des routeurs inclus (FastAPI >= 0.16x)."""

from collections.abc import Callable, Iterator, Sequence
from typing import Any

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import get_dependant
from fastapi.routing import APIRoute


def _extra_calls(*groups: Sequence[Any]) -> list[Callable[..., Any]]:
    calls: list[Callable[..., Any]] = []
    for group in groups:
        for dep in group:
            call = getattr(dep, "dependency", None)
            if call is not None:
                calls.append(call)
    return calls


def iter_api_routes(
    routes: Sequence[Any], inherited: Sequence[Callable[..., Any]] = ()
) -> Iterator[tuple[APIRoute, list[Callable[..., Any]]]]:
    for route in routes:
        if isinstance(route, APIRoute):
            yield route, list(inherited)
        elif hasattr(route, "original_router"):
            router = route.original_router
            extra = [
                *inherited,
                *_extra_calls(route.include_context.dependencies, router.dependencies),
            ]
            yield from iter_api_routes(router.routes, extra)


def api_routes(app: FastAPI) -> list[tuple[APIRoute, list[Callable[..., Any]]]]:
    return list(iter_api_routes(app.routes))


def dependency_calls(dependant: Dependant) -> Iterator[Callable[..., Any] | None]:
    for sub in dependant.dependencies:
        yield sub.call
        yield from dependency_calls(sub)


def route_depends_on(
    route: APIRoute, inherited: Sequence[Callable[..., Any]], target: object
) -> bool:
    if target in set(dependency_calls(route.dependant)):
        return True
    for call in inherited:
        if call is target:
            return True
        if target in set(dependency_calls(get_dependant(path="", call=call))):
            return True
    return False
