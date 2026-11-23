"""Gestionnaire d'erreurs global : ni valeurs saisies ni messages bruts (N-05, N-08)."""

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = structlog.get_logger()


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Seuls l'emplacement et le type de l'erreur sont renvoyés : jamais la valeur saisie.
    errors: list[dict[str, Any]] = [
        {"loc": [str(p) for p in e["loc"]], "type": e["type"]} for e in exc.errors()
    ]
    log.info("validation_error", path=request.url.path, error_count=len(errors))
    return JSONResponse(status_code=422, content={"detail": errors})


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    log.info("http_error", path=request.url.path, status=exc.status_code)
    return JSONResponse(
        status_code=exc.status_code, content={"detail": "error"}, headers=exc.headers
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Le message d'une exception peut contenir une donnée patient : seul le type est journalisé.
    log.error("unhandled_error", path=request.url.path, error_type=type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "internal_error"})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
