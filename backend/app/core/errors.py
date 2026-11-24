"""Gestionnaire d'erreurs global : ni valeurs saisies ni messages bruts (N-05, N-08)."""

from typing import Any, cast

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.errors import SafeError

log = structlog.get_logger()


def route_template(request: Request) -> str:
    """Gabarit de route (ex. /items/{id}), jamais l'URL réelle qui peut porter une donnée."""
    return str(getattr(request.scope.get("route"), "path", "unmatched"))


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Seuls l'emplacement et le type de l'erreur sont renvoyés : jamais la valeur saisie.
    errors: list[dict[str, Any]] = [
        {"loc": [str(p) for p in e["loc"]], "type": e["type"]}
        for e in cast(RequestValidationError, exc).errors()
    ]
    log.info("validation_error", route=route_template(request), error_count=len(errors))
    return JSONResponse(status_code=422, content={"detail": errors})


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    http_exc = cast(StarletteHTTPException, exc)
    log.info("http_error", route=route_template(request), status=http_exc.status_code)
    return JSONResponse(
        status_code=http_exc.status_code, content={"detail": "error"}, headers=http_exc.headers
    )


SAFE_STATUS = {
    "authentication_required": 401,
    "session_invalid": 401,
    "mfa_required": 403,
    "forbidden": 403,
    "not_found": 404,
    "identity_provider_unavailable": 503,
}


async def safe_error_handler(request: Request, exc: Exception) -> JSONResponse:
    code = cast(SafeError, exc).code
    status = SAFE_STATUS.get(code, 400)
    log.info("safe_error", route=route_template(request), code=code, status=status)
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return JSONResponse(status_code=status, content={"detail": code}, headers=headers)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Le message d'une exception peut contenir une donnée patient : seul le type est journalisé.
    log.error("unhandled_error", route=route_template(request), error_type=type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "internal_error"})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(SafeError, safe_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
