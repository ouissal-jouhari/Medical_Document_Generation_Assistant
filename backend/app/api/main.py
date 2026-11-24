import time
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response

from app.api.routes.consultations import router as consultations_router
from app.api.routes.health import router as health_router
from app.api.routes.me import router as me_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers, route_template
from app.core.logging import configure_logging

log = structlog.get_logger()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_dir, settings.log_retention_days)
    app = FastAPI(
        title="XeleronIA", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None
    )
    register_error_handlers(app)

    @app.middleware("http")
    async def access_log(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        log.info(
            "request",
            method=request.method,
            route=route_template(request),
            status=response.status_code,
            duration_ms=round((time.perf_counter() - start) * 1000, 1),
        )
        return response

    app.include_router(health_router)
    app.include_router(me_router)
    app.include_router(consultations_router)
    return app


app = create_app()
