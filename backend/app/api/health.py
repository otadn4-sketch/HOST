from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_db
from app.config import Settings, get_settings
from app.services.scanner import ping

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    return {"status": "ok"}


@router.get("/api/ready")
def ready(db: DBSession = Depends(get_db), settings: Settings = Depends(get_settings)):
    db.execute(text("SELECT 1"))
    clam = True if settings.clamav_disabled else ping(settings.clamd_host, settings.clamd_port)
    from app.services.backup import backup_path_is_isolated

    isolated = backup_path_is_isolated(settings)
    return {
        "status": "ready" if isolated else "degraded",
        "database": True,
        "clamav": clam,
        "backup_path_isolated": isolated,
    }
