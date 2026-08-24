from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db, require_system_admin
from app.models.entities import FaranSyncRecord, FileObject, User
from app.services.audit import write_audit
from app.services.faran import FaranClient, record_sync

router = APIRouter(prefix="/api/faran", tags=["faran"])


@router.get("/status")
def faran_status(user: User = Depends(get_current_user)):
    return {"faran": FaranClient().status()}


@router.get("/syncs")
def faran_syncs(
    db: DBSession = Depends(get_db),
    user: User = Depends(require_system_admin),
):
    rows = db.query(FaranSyncRecord).order_by(FaranSyncRecord.started_at.desc()).limit(50).all()
    return {
        "syncs": [
            {
                "id": r.id,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "status": r.status,
                "direction": r.direction,
                "items_count": r.items_count,
                "error": r.error,
            }
            for r in rows
        ]
    }


@router.post("/sync")
def faran_sync(
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_system_admin),
):
    client = FaranClient()
    files = db.query(FileObject).filter(FileObject.is_deleted.is_(False), FileObject.is_current_version.is_(True)).limit(200).all()
    ping = client.ping()
    pushed = client.push_metadata(files)
    daily = client.daily_read()
    row = record_sync(db, user_id=user.id, direction="push_metadata", result=pushed)
    write_audit(
        db,
        user=user,
        action="faran_sync",
        target_resource="faran",
        target_type="integration",
        target_id=row.id,
        details="همگام‌سازی stub با سامانه فاران",
        request=request,
    )
    return {
        "sync": {
            "id": row.id,
            "status": row.status,
            "ping": ping,
            "push": {"queued": pushed.get("queued", 0), "mode": pushed.get("mode")},
            "daily_read": daily,
        }
    }
