from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

logger = logging.getLogger("ai_sports_travel_planner")
FRONTEND_DIST_ENV_VAR = "FRONTEND_DIST_DIR"
DEFAULT_FRONTEND_DIST_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"


def create_app(frontend_dist_dir: Path | None = None) -> FastAPI:
    _configure_logging()
    app = FastAPI(title="AI Sports Travel Planner")
    app.include_router(router, prefix="/api")

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled application error.",
                extra={"path": request.url.path, "method": request.method},
            )
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "Request handled.",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    dist_dir = frontend_dist_dir or _resolve_frontend_dist_dir()
    if dist_dir.exists():
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def serve_frontend(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)

            requested_path = dist_dir / full_path
            if full_path and requested_path.exists() and requested_path.is_file():
                return FileResponse(requested_path)

            index_path = dist_dir / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return JSONResponse({"detail": "Frontend not built"}, status_code=404)

    return app


def _resolve_frontend_dist_dir() -> Path:
    configured = os.getenv(FRONTEND_DIST_ENV_VAR)
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_FRONTEND_DIST_DIR


def _configure_logging() -> None:
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
