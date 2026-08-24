from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import ai, auth, dashboard, faran, files, graph, groups, health, logs, meetings, phases, recipients, roles, scrub, settings as settings_api, shares, transactions, updates, users
from app.config import get_settings
from app.db import Base, make_engine, make_session_factory
from app.models import entities  # noqa: F401
from app.services.bootstrap import bootstrap_schema, seed_dev_users


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
            "frame-src 'self' blob:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


def create_app(overrides: dict | None = None) -> FastAPI:
    settings = get_settings()
    if overrides:
        for key, value in overrides.items():
            setattr(settings, key, value)

    app = FastAPI(title="سامانه اشتراک‌گذاری فایل شبکه کانون‌های تفکر ایران «ایتان»", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(groups.router)
    app.include_router(roles.router)
    app.include_router(files.router)
    app.include_router(ai.router)
    app.include_router(logs.router)
    app.include_router(dashboard.router)
    app.include_router(settings_api.router)
    app.include_router(updates.router)
    app.include_router(phases.router)
    app.include_router(transactions.router)
    app.include_router(recipients.router)
    app.include_router(meetings.router)
    app.include_router(faran.router)
    app.include_router(shares.router)
    app.include_router(graph.router)
    app.include_router(scrub.router)

    @app.on_event("startup")
    def _startup() -> None:
        from app.api import deps
        from app.services.update_watch import start_update_stamp_watch

        engine = make_engine(settings.database_url)
        Base.metadata.create_all(engine)
        deps._engine = engine
        deps._SessionLocal = make_session_factory(engine)
        settings.vault_path.mkdir(parents=True, exist_ok=True)
        settings.quarantine_path.mkdir(parents=True, exist_ok=True)
        settings.backup_path.mkdir(parents=True, exist_ok=True)
        settings.staging_path.mkdir(parents=True, exist_ok=True)
        settings.releases_path.mkdir(parents=True, exist_ok=True)
        db = deps._SessionLocal()
        try:
            bootstrap_schema(db)
            seed_dev_users(db, settings)
            db.commit()
        finally:
            db.close()
        start_update_stamp_watch()

    return app


app = create_app()
