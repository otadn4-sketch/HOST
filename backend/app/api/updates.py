from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_db, require_system_admin
from app.config import Settings, get_settings, unsigned_updates_allowed
from app.models.entities import MaintenanceState, SystemUpdate, User
from app.services.audit import write_audit
from app.services.files import stream_to_quarantine
from app.services.release_bundle import current_version, is_compatible, verify_and_extract
from app.services.updater import apply_extracted_release, delayed_reload_stamp, maybe_upgrade_alembic

router = APIRouter(prefix="/api/updates", tags=["updates"])

RETRYABLE = {"validated", "failed", "rolled_back", "installing"}


def _maint(db: DBSession) -> MaintenanceState:
    row = db.query(MaintenanceState).filter(MaintenanceState.id == 1).one_or_none()
    if row is None:
        row = MaintenanceState(id=1, enabled=False)
        db.add(row)
        db.flush()
    return row


def _serialize(row: SystemUpdate) -> dict:
    return {
        "id": row.id,
        "version": row.version,
        "compatible_from": row.compatible_from,
        "changelog": row.changelog,
        "status": row.status,
        "uploaded_by": row.uploaded_by,
        "created_at": row.created_at,
        "error": row.error,
        "migration_id": row.migration_id,
    }


@router.get("")
def list_updates(db: DBSession = Depends(get_db), user: User = Depends(require_system_admin)):
    rows = db.query(SystemUpdate).order_by(SystemUpdate.created_at.desc()).limit(50).all()
    return {
        "current_version": current_version(Path("/app") if Path("/app/VERSION").exists() else Path(".")),
        "maintenance": _maint(db).enabled,
        "updates": [_serialize(r) for r in rows],
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
    result = verify_and_extract(
        staging_file,
        settings.update_public_key,
        extract_dir,
        allow_unsigned=unsigned_updates_allowed(settings),
    )
    shutil.rmtree(extract_dir, ignore_errors=True)
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
        migration_id=(result.manifest or {}).get("migration_id", "") or "",
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
    return {"update": _serialize(update)}


@router.post("/{update_id}/confirm")
def confirm_update(
    update_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_system_admin),
    settings: Settings = Depends(get_settings),
):
    update = db.query(SystemUpdate).filter(SystemUpdate.id == update_id).one_or_none()
    if update is None:
        raise HTTPException(status_code=404, detail="بسته به‌روزرسانی یافت نشد.")
    if update.status not in RETRYABLE:
        raise HTTPException(
            status_code=400,
            detail=f"این بسته در وضعیت «{update.status}» قابل نصب نیست. اگر نصب قبلی ناموفق بود، دوباره بارگذاری کنید.",
        )
    bundle = settings.staging_path / update.staging_name
    if not bundle.is_file():
        update.status = "failed"
        update.error = "فایل بسته در staging موجود نیست. دوباره بارگذاری کنید."
        raise HTTPException(status_code=400, detail=update.error)

    maint = _maint(db)
    maint.enabled = True
    maint.reason = f"نصب نسخه {update.version}"
    update.status = "installing"
    update.error = ""
    write_audit(
        db,
        user=user,
        action="system_update",
        target_resource=update.version,
        target_type="update",
        target_id=update.id,
        details="تأیید نهایی مدیر و نصب مستقیم روی سامانه",
        severity="warning",
        request=request,
    )
    db.commit()

    work = settings.staging_path / f"install-{update.id}"
    try:
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)
        result = verify_and_extract(
            bundle,
            settings.update_public_key,
            work,
            allow_unsigned=unsigned_updates_allowed(settings),
        )
        if not result.ok:
            raise RuntimeError("; ".join(result.errors) or "اعتبارسنجی بسته ناموفق بود.")
        notes = apply_extracted_release(work)
        alembic_note = maybe_upgrade_alembic()
        notes.append(alembic_note)
        update.status = "success"
        update.error = ""
        maint.enabled = False
        write_audit(
            db,
            user=user,
            action="system_update",
            target_resource=update.version,
            target_type="update",
            target_id=update.id,
            details="نصب موفق: " + "؛ ".join(notes),
            request=request,
        )
        background_tasks.add_task(delayed_reload_stamp)
        return {"ok": True, "update_id": update.id, "status": update.status, "notes": notes}
    except HTTPException:
        raise
    except Exception as exc:
        update.status = "failed"
        update.error = str(exc)[:2000]
        maint.enabled = False
        write_audit(
            db,
            user=user,
            action="system_update",
            target_resource=update.version,
            details=f"نصب ناموفق: {update.error}",
            severity="critical",
            request=request,
        )
        raise HTTPException(status_code=500, detail=f"نصب ناموفق بود: {update.error}") from exc
    finally:
        shutil.rmtree(work, ignore_errors=True)
