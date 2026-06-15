from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request

from app.observability.context import request_id_context
from app.observability.logging import safe_log_extra
from app.observability.metrics import get_metrics_recorder

LOGGER = logging.getLogger("snowcast.request")


def add_observability_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex}"
        token = request_id_context.set(request_id)
        start = time.perf_counter()
        status_code = 500
        response = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            status_class = f"{status_code // 100}xx"
            route = request.scope.get("route")
            route_path = getattr(route, "path", "__unknown__")
            attributes = {
                "route": route_path,
                "method": request.method,
                "status_class": status_class,
            }
            recorder = get_metrics_recorder()
            recorder.increment("snowcast_http_requests_total", attributes)
            recorder.observe(
                "snowcast_http_request_duration_seconds",
                duration_ms / 1000,
                attributes,
            )
            LOGGER.info(
                "Request handled.",
                extra=safe_log_extra(
                    {
                        "event": "http.request.completed",
                        "request_id": request_id,
                        "route": route_path,
                        "method": request.method,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                    }
                ),
            )
            if response is not None:
                response.headers["x-request-id"] = request_id
            request_id_context.reset(token)
