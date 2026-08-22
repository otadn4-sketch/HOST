from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_db, require_system_admin
from app.config import Settings, get_settings
from app.models.entities import MaintenanceState, SystemUpdate, User
from app.services.audit import write_audit
from app.services.files import stream_to_quarantine
from app.services.release_bundle import current_version, is_compatible, verify_and_extract

router = APIRouter(prefix="/api/updates", tags=["updates"])


def _maint(db: DBSession) -> MaintenanceState:
    row = db.query(MaintenanceState).filter(MaintenanceState.id == 1).one_or_none()
    if row is None:
        row = MaintenanceState(id=1, enabled=False)
        db.add(row)
        db.flush()
    return row


@router.get("")
def list_updates(db: DBSession = Depends(get_db), user: User = Depends(require_system_admin)):
    rows = db.query(SystemUpdate).order_by(SystemUpdate.created_at.desc()).limit(50).all()
    root = Path("/opt/eytan")
    return {
        "current_version": current_version(Path("/app") if Path("/app/VERSION").exists() else Path(".")),
        "maintenance": _maint(db).enabled,
        "updates": [
            {
                "id": r.id,
                "version": r.version,
                "compatible_from": r.compatible_from,
                "changelog": r.changelog,
                "status": r.status,
                "uploaded_by": r.uploaded_by,
                "created_at": r.created_at,
                "error": r.error,
                "migration_id": r.migration_id,
            }
            for r in rows
        ],
    }


@router.post("/upload")
async def upload_bundle(
    request: Request,
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db),
    user: User = Depends(require_system_admin),
    settings: Settings = Depends(get_settings),
):
    if not (file.filename or "").endswith(".eytan.zip") and not (file.filename or "").endswith(".zip"):
        raise HTTPException(status_code=400, detail="بسته باید فایل zip امضاشده باشد.")
    settings.staging_path.mkdir(parents=True, exist_ok=True)
    staging_name = f"bundle-{uuid.uuid4().hex}.zip"
    staging_file = settings.staging_path / staging_name
    size, digest = await stream_to_quarantine(file, staging_file, 200 * 1024 * 1024)
    extract_dir = settings.staging_path / f"extracted-{uuid.uuid4().hex}"
    result = verify_and_extract(staging_file, settings.update_public_key, extract_dir, allow_unsigned=True)
    status = "validated" if result.ok else "rejected"
    update = SystemUpdate(
        version=(result.manifest or {}).get("version", "unknown"),
        compatible_from=(result.manifest or {}).get("compatible_from", ""),
        changelog=(result.manifest or {}).get("changelog", ""),
        status=status,
        bundle_sha256=digest,
        staging_name=staging_name,
        uploaded_by=user.id,
        error="; ".join(result.errors),
        migration_id=(result.manifest or {}).get("migration_id", ""),
        manifest=result.manifest or {},
    )
    if result.ok and not (result.manifest or {}).get("unsigned_source"):
        current = current_version(Path("/app") if Path("/app/VERSION").exists() else Path("."))
        if not is_compatible(current, update.compatible_from or "0.0.0", update.version):
            update.status = "rejected"
            update.error = f"ناسازگار با نسخه فعلی {current}"
            status = "rejected"
    db.add(update)
    db.flush()
    write_audit(
        db,
        user=user,
        action="system_update",
        target_resource=update.version,
        target_type="update",
        target_id=update.id,
        details=f"بارگذاری بسته به‌روزرسانی ({status})",
        severity="warning" if status == "validated" else "critical",
        request=request,
    )
    return {
        "update": {
            "id": update.id,
            "version": update.version,
            "compatible_from": update.compatible_from,
            "changelog": update.changelog,
            "status": update.status,
            "error": update.error,
            "migration_id": update.migration_id,
        }
    }


@router.post("/{update_id}/confirm")
def confirm_update(
    update_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_system_admin),
    settings: Settings = Depends(get_settings),
):
    update = db.query(SystemUpdate).filter(SystemUpdate.id == update_id).one_or_none()
    if update is None:
        raise HTTPException(status_code=404, detail="بسته به‌روزرسانی یافت نشد.")
    if update.status != "validated":
        raise HTTPException(status_code=400, detail="بسته برای نصب تأیید نشده است.")
    maint = _maint(db)
    maint.enabled = True
    maint.reason = f"نصب نسخه {update.version}"
    update.status = "installing"
    write_audit(
        db,
        user=user,
        action="system_update",
        target_resource=update.version,
        target_type="update",
        target_id=update.id,
        details="تأیید نهایی مدیر و ارسال به update-agent",
        severity="warning",
        request=request,
    )
    db.commit()
    try:
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(
                f"{settings.update_agent_url}/install",
                headers={"X-Update-Token": settings.update_agent_token},
                json={
                    "update_id": update.id,
                    "staging_name": update.staging_name,
                    "version": update.version,
                    "migration_id": update.migration_id,
                    "initiated_by": user.id,
                },
            )
            body = resp.json()
    except Exception as exc:
        update.status = "failed"
        update.error = str(exc)
        maint.enabled = False
        write_audit(
            db,
            user=user,
            action="system_update",
            target_resource=update.version,
            details=f"ارتباط با update-agent ناموفق: {exc}",
            severity="critical",
            request=request,
        )
        raise HTTPException(status_code=502, detail="عامل به‌روزرسانی در دسترس نیست.") from exc

    if not body.get("ok"):
        update.status = "failed" if not body.get("rolled_back") else "rolled_back"
        update.error = body.get("error", "install failed")
        update.rollback_result = body.get("rollback", "")
        maint.enabled = False
        write_audit(
            db,
            user=user,
            action="system_update",
            target_resource=update.version,
            details=update.error,
            severity="critical",
            request=request,
        )
        raise HTTPException(status_code=500, detail="نصب ناموفق بود و rollback انجام شد." if body.get("rolled_back") else "نصب ناموفق بود.")
    update.status = "success"
    maint.enabled = False
    write_audit(
        db,
        user=user,
        action="system_update",
        target_resource=update.version,
        details="نصب موفق بسته امضاشده",
        request=request,
    )
    return {"ok": True, "update_id": update.id, "status": update.status}
