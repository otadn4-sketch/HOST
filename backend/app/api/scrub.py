from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db
from app.config import get_settings
from app.models.entities import DocumentScrubJob, FileObject, User, utcnow
from app.schemas import ScrubJobIn
from app.security.rbac import evaluate_file_access
from app.services.audit import write_audit
from app.services.document_scrub import apply_scrub, plan_scrub
from app.services.files import ingest_file, stored_file_path

router = APIRouter(prefix="/api/scrub", tags=["scrub"])


@router.post("/jobs")
def create_scrub_job(
    payload: ScrubJobIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    file = db.query(FileObject).filter(FileObject.id == payload.file_id, FileObject.is_deleted.is_(False)).one_or_none()
    if file is None:
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    access = evaluate_file_access(user, file, file.permissions)
    if not access.can_manage:
        raise HTTPException(status_code=403, detail="برای پالایش سند مجوز مدیریت فایل لازم است.")
    if file.scan_status != "clean":
        raise HTTPException(status_code=400, detail="فقط فایل پویش‌شده و پاک قابل پالایش است.")

    plan = plan_scrub(payload.rules)
    settings = get_settings()
    try:
        src = stored_file_path(settings, file)
        data = src.read_bytes()
    except Exception:
        job = DocumentScrubJob(
            file_id=file.id,
            status="unavailable",
            rules=plan["rules"],
            notes="خواندن فایل برای پالایش ممکن نشد؛ فایل اصلی تغییر نکرد و امن تلقی نشد.",
            created_by=user.id,
            finished_at=utcnow(),
            redacted_count=0,
        )
        db.add(job)
        db.flush()
        return {"job": _serialize_job(job)}

    result = apply_scrub(
        data,
        extension=file.extension or "",
        mime=file.detected_mime or file.mime_type or "",
        rules=plan["rules"],
    )
    job = DocumentScrubJob(
        file_id=file.id,
        status=result["status"],
        rules=result["rules"],
        notes=result["note"],
        created_by=user.id,
        finished_at=utcnow(),
        redacted_count=int(result.get("redacted_count") or 0),
    )
    db.add(job)
    db.flush()

    if result.get("applied") and result.get("output") is not None:
        qpath = settings.quarantine_path / f"scrub-{job.id}"
        qpath.write_bytes(result["output"])
        digest = hashlib.sha256(result["output"]).hexdigest()
        original = Path(file.original_name or "document.txt").name
        stem = Path(original).stem
        suffix = Path(original).suffix
        scrubbed_name = f"{stem}-scrubbed{suffix}"
        new_file = ingest_file(
            db,
            settings,
            user=user,
            request=request,
            quarantine_path=qpath,
            size=len(result["output"]),
            sha256=digest,
            original_name=scrubbed_name,
            title=f"{file.title} (پالایش‌شده)",
            topic=file.topic,
            group_id=file.group_id,
            classification=file.classification,
            description="نسخه پالایش‌شده؛ فایل اصلی بدون تغییر ماند.",
            tags=list(file.tags or []),
            parent_file_id=None,
            permission_specs=None,
        )
        job.result_file_id = new_file.id

    write_audit(
        db,
        user=user,
        action="document_scrub",
        target_resource=file.title,
        target_type="file",
        target_id=file.id,
        details=f"پالایش سند: {job.status}",
        request=request,
    )
    return {"job": _serialize_job(job)}


def _serialize_job(job: DocumentScrubJob) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "rules": job.rules,
        "notes": job.notes,
        "file_id": job.file_id,
        "result_file_id": job.result_file_id,
        "redacted_count": job.redacted_count,
        "applied": job.status == "completed",
    }
