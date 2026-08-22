from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db
from app.config import Settings, get_settings
from app.models.entities import FileObject, FilePermission, User, utcnow
from app.schemas import FileMetaPatchIn
from app.security.rbac import can_upload, evaluate_file_access, is_admin
from app.services.audit import write_audit
from app.services.files import get_visible_file, ingest_file, serialize_file, stream_to_quarantine, vault_abs
from app.services.policy import get_or_create_policy

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("")
def list_files(
    q: str = "",
    group_id: str | None = None,
    topic: str | None = None,
    classification: str | None = None,
    scan_status: str | None = None,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(FileObject)
        .filter(FileObject.is_deleted.is_(False), FileObject.is_current_version.is_(True))
        .order_by(FileObject.created_at.desc())
        .all()
    )
    result = []
    for file in rows:
        access = evaluate_file_access(user, file, file.permissions)
        if not access.can_view:
            continue
        if group_id and file.group_id != group_id:
            continue
        if topic and topic != "all" and file.topic != topic:
            continue
        if classification and classification != "all" and file.classification != classification:
            continue
        if scan_status and scan_status != "all" and file.scan_status != scan_status:
            continue
        if q.strip():
            blob_parts = [
                file.title or "",
                file.original_name or "",
                file.topic or "",
                " ".join(file.tags or []),
            ]
            if is_admin(user):
                blob_parts.append(file.sha256)
            blob = " ".join(blob_parts).lower()
            if q.strip().lower() not in blob:
                continue
        result.append(serialize_file(db, file, user))
    return {"files": result}


@router.get("/{file_id}")
def file_detail(
    file_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    file, access = get_visible_file(db, user, file_id)
    if file is None:
        write_audit(
            db,
            user=user,
            action="suspicious_activity",
            target_resource=file_id,
            details="تلاش برای مشاهده فایل بدون مجوز یا شناسه نامعتبر",
            severity="warning",
            request=request,
            target_type="file",
            target_id=file_id,
        )
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    file.view_count += 1
    write_audit(
        db,
        user=user,
        action="file_view",
        target_resource=file.title,
        target_type="file",
        target_id=file.id,
        details="مشاهده جزئیات فایل",
        request=request,
    )
    payload = serialize_file(db, file, user)
    versions = (
        db.query(FileObject)
        .filter(
            FileObject.is_deleted.is_(False),
            (FileObject.id == file.id) | (FileObject.parent_file_id == (file.parent_file_id or file.id)) | (FileObject.parent_file_id == file.id),
        )
        .order_by(FileObject.version_number.desc())
        .all()
    )
    visible_versions = []
    for v in versions:
        if evaluate_file_access(user, v, v.permissions).can_view or v.id == file.id:
            visible_versions.append(
                {"id": v.id, "version": v.version, "created_at": v.created_at, "scan_status": v.scan_status}
            )
    payload["versions"] = visible_versions
    return {"file": payload}


@router.post("")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(""),
    topic: str = Form(""),
    group_id: str = Form(""),
    classification: str = Form("internal"),
    description: str = Form(""),
    tags: str = Form(""),
    permissions_json: str = Form("[]"),
    parent_file_id: str = Form(""),
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    if not can_upload(user):
        raise HTTPException(status_code=403, detail="شما مجوز بارگذاری ندارید.")
    if classification not in {"public", "internal", "confidential", "secret"}:
        raise HTTPException(status_code=400, detail="رده محرمانگی نامعتبر است.")
    policy = get_or_create_policy(db)
    qname = f"up-{uuid.uuid4().hex}.part"
    qpath = settings.quarantine_path / qname
    size, digest = await stream_to_quarantine(file, qpath, policy.max_file_size_bytes)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    try:
        specs = json.loads(permissions_json or "[]")
        if not isinstance(specs, list):
            specs = []
    except json.JSONDecodeError:
        specs = []
    created = ingest_file(
        db,
        settings,
        user=user,
        request=request,
        quarantine_path=qpath,
        size=size,
        sha256=digest,
        original_name=file.filename or "file.bin",
        title=title,
        topic=topic,
        group_id=group_id or user.group_id,
        classification=classification,
        description=description,
        tags=tag_list,
        parent_file_id=parent_file_id or None,
        permission_specs=specs,
    )
    return {"file": serialize_file(db, created, user)}


@router.get("/{file_id}/download")
def download_file(
    file_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    file, access = get_visible_file(db, user, file_id)
    if file is None or not access.can_download:
        write_audit(
            db,
            user=user,
            action="suspicious_activity",
            target_resource=file_id,
            details="تلاش غیرمجاز برای دریافت فایل",
            severity="warning",
            request=request,
            target_type="file",
            target_id=file_id,
        )
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    if file.scan_status != "clean":
        raise HTTPException(status_code=403, detail="فایل قرنطینه یا مشکوک قابل دریافت نیست.")
    path = vault_abs(settings, file.storage_relpath)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    file.download_count += 1
    write_audit(
        db,
        user=user,
        action="file_download",
        target_resource=file.title,
        target_type="file",
        target_id=file.id,
        details="دریافت از طریق endpoint مجاز",
        request=request,
    )

    def iterator():
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk

    filename = Path(file.original_name).name.replace('"', "")
    return StreamingResponse(
        iterator(),
        media_type=file.detected_mime or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
            "Content-Length": str(file.size_bytes),
        },
    )


@router.patch("/{file_id}")
def patch_file(
    file_id: str,
    payload: FileMetaPatchIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    file, access = get_visible_file(db, user, file_id)
    if file is None or not access.can_manage:
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    if payload.title:
        file.title = payload.title
    if payload.topic is not None:
        file.topic = payload.topic
    if payload.description is not None:
        file.description = payload.description
    if payload.classification:
        if payload.classification not in {"public", "internal", "confidential", "secret"}:
            raise HTTPException(status_code=400, detail="رده محرمانگی نامعتبر است.")
        file.classification = payload.classification
    if payload.tags is not None:
        file.tags = payload.tags
    if payload.group_id is not None and is_admin(user):
        file.group_id = payload.group_id or None
    if payload.permissions is not None:
        db.query(FilePermission).filter(FilePermission.file_id == file.id).delete()
        for spec in payload.permissions:
            db.add(
                FilePermission(
                    file_id=file.id,
                    target_type=spec.target_type,
                    target_id=spec.target_id,
                    can_view=spec.can_view,
                    can_download=spec.can_download,
                    can_upload=spec.can_upload,
                    can_manage=spec.can_manage,
                    granted_by=user.id,
                )
            )
        write_audit(
            db,
            user=user,
            action="permission_change",
            target_resource=file.title,
            target_type="file",
            target_id=file.id,
            details="به‌روزرسانی مجوزهای فایل",
            request=request,
        )
    file.updated_at = utcnow()
    db.refresh(file)
    return {"file": serialize_file(db, file, user)}


@router.delete("/{file_id}")
def delete_file(
    file_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    file, access = get_visible_file(db, user, file_id)
    if file is None or not access.can_manage:
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    file.is_deleted = True
    try:
        if file.scan_status == "clean":
            vault_abs(settings, file.storage_relpath).unlink(missing_ok=True)
        else:
            (settings.quarantine_path / file.storage_relpath).unlink(missing_ok=True)
    except Exception:
        pass
    write_audit(
        db,
        user=user,
        action="file_quarantined",
        target_resource=file.title,
        target_type="file",
        target_id=file.id,
        details="حذف فایل از مخزن",
        severity="warning",
        request=request,
    )
    return {"ok": True}
