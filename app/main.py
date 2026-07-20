from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    Response,
)
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.routing import Match
from starlette.types import Scope

from app.api.public_errors import (
    branded_html_response,
    install_public_error_handlers,
)
from app.api.routes import router
from app.observability.logging import configure_logging
from app.observability.middleware import add_observability_middleware
from app.observability.otel import configure_observability
from app.public_pages import (
    render_public_destination_page,
    render_robots_txt,
    render_sitemap_xml,
)

FRONTEND_DIST_ENV_VAR = "FRONTEND_DIST_DIR"
DEFAULT_FRONTEND_DIST_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"


def create_app(frontend_dist_dir: Path | None = None) -> FastAPI:
    configure_logging()
    app = FastAPI(title="Snowcast")
    configure_observability(app)
    add_observability_middleware(app)
    install_public_error_handlers(app)
    app.include_router(router, prefix="/api")

    @app.get("/ski-destinations/{stay_destination_id}", include_in_schema=False)
    def serve_public_destination_page(
        stay_destination_id: str,
        request: Request,
    ) -> HTMLResponse:
        try:
            return HTMLResponse(
                render_public_destination_page(
                    stay_destination_id=stay_destination_id,
                    base_url=_request_base_url(request),
                )
            )
        except HTTPException as error:
            if error.status_code != 404:
                raise
            return branded_html_response(
                status_code=404,
                title="Destination not found",
                heading="We could not find this ski destination",
                explanation=(
                    "The destination may have changed or may not be available in "
                    "Snowcast yet."
                ),
                return_href="/",
                return_label="Return to search",
            )

    @app.get("/sitemap.xml", include_in_schema=False)
    def serve_sitemap(request: Request) -> Response:
        return Response(
            render_sitemap_xml(base_url=_request_base_url(request)),
            media_type="application/xml",
        )

    @app.get("/robots.txt", include_in_schema=False)
    def serve_robots(request: Request) -> PlainTextResponse:
        return PlainTextResponse(render_robots_txt(base_url=_request_base_url(request)))

    dist_dir = frontend_dist_dir or _resolve_frontend_dist_dir()
    if dist_dir.exists():
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        def serve_frontend(full_path: str):
            requested_path = dist_dir / full_path
            if full_path and requested_path.exists() and requested_path.is_file():
                return FileResponse(requested_path)

            index_path = dist_dir / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return JSONResponse({"detail": "Frontend not built"}, status_code=404)

        # The SPA fallback must never participate in API method matching.
        app.router.routes.append(
            _FrontendCatchAllRoute(
                "/{full_path:path}",
                serve_frontend,
                methods=["GET"],
                include_in_schema=False,
            )
        )

    return app


class _FrontendCatchAllRoute(APIRoute):
    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        if scope["type"] == "http" and (
            scope["path"] == "/api" or scope["path"].startswith("/api/")
        ):
            return Match.NONE, {}
        return super().matches(scope)


def _request_base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _resolve_frontend_dist_dir() -> Path:
    configured = os.getenv(FRONTEND_DIST_ENV_VAR)
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_FRONTEND_DIST_DIR


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
