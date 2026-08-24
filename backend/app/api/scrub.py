from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db
from app.models.entities import DocumentScrubJob, FileObject, User
from app.schemas import ScrubJobIn
from app.security.rbac import evaluate_file_access
from app.services.audit import write_audit
from app.services.document_scrub import plan_scrub
from app.services.phases import require_phase

router = APIRouter(prefix="/api/scrub", tags=["scrub"])


@router.post("/jobs")
def create_scrub_job(
    payload: ScrubJobIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_phase("phase_5_security_graph_enabled", "فاز ۵ (پالایش سند) فعال نیست.")
    file = db.query(FileObject).filter(FileObject.id == payload.file_id, FileObject.is_deleted.is_(False)).one_or_none()
    if file is None:
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    access = evaluate_file_access(user, file, file.permissions)
    if not access.can_manage:
        raise HTTPException(status_code=403, detail="برای پالایش سند مجوز مدیریت فایل لازم است.")
    plan = plan_scrub(payload.rules)
    job = DocumentScrubJob(
        file_id=file.id,
        status="stub",
        rules=plan["rules"],
        notes=plan["note"],
        created_by=user.id,
    )
    db.add(job)
    db.flush()
    write_audit(
        db,
        user=user,
        action="document_scrub_stub",
        target_resource=file.title,
        target_type="file",
        target_id=file.id,
        details="صف پالایش سند (stub فاز ۵)",
        request=request,
    )
    return {"job": {"id": job.id, "status": job.status, "rules": job.rules, "notes": job.notes, "file_id": job.file_id}}
