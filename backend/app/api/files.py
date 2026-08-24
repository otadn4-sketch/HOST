from __future__ import annotations

import json
import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db
from app.config import Settings, get_settings
from app.models.entities import FileObject, FilePermission, User, utcnow
from app.schemas import FileMetaPatchIn
from app.security.rbac import can_upload, evaluate_file_access, is_admin
from app.services.audit import write_audit
from app.services.file_types import extract_office_preview_text
from app.services.files import get_visible_file, ingest_file, is_malware_hit, serialize_file, stored_file_path, stream_to_quarantine
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
    if is_malware_hit(file):
        raise HTTPException(status_code=403, detail="فایل قرنطینه یا مشکوک قابل دریافت نیست.")
    path = stored_file_path(settings, file)
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
    return _stream_file(file, path, inline=False)


@router.get("/{file_id}/preview")
def preview_file(
    file_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    file, access = get_visible_file(db, user, file_id)
    if file is None or not access.can_view:
        write_audit(
            db,
            user=user,
            action="suspicious_activity",
            target_resource=file_id,
            details="تلاش غیرمجاز برای پیش‌نمایش فایل",
            severity="warning",
            request=request,
            target_type="file",
            target_id=file_id,
        )
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    if is_malware_hit(file) and not is_admin(user):
        raise HTTPException(status_code=403, detail="این فایل قابل پیش‌نمایش نیست.")
    path = stored_file_path(settings, file)
    file.view_count += 1
    write_audit(
        db,
        user=user,
        action="file_preview",
        target_resource=file.title,
        target_type="file",
        target_id=file.id,
        details="پیش‌نمایش محتوای فایل",
        request=request,
    )
    extracted = extract_office_preview_text(path, file.extension or file.original_name)
    if extracted:
        payload = extracted.encode("utf-8")
        return Response(
            content=payload,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": "inline; filename=\"preview.txt\"",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
                "X-Eytan-Preview": "extracted-text",
            },
        )
    return _stream_file(file, path, inline=True)


@router.post("/{file_id}/preview-heartbeat")
def preview_heartbeat(
    file_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    file, access = get_visible_file(db, user, file_id)
    if file is None or not access.can_view:
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    write_audit(
        db,
        user=user,
        action="file_preview_heartbeat",
        target_resource=file.title,
        target_type="file",
        target_id=file.id,
        details="حضور در بخش پیش‌نمایش",
        request=request,
    )
    return {"ok": True}


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
        stored_file_path(settings, file).unlink(missing_ok=True)
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


def _stream_file(file: FileObject, path: Path, *, inline: bool) -> StreamingResponse:
    def iterator():
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk

    filename = Path(file.original_name).name.replace('"', "")
    ascii_name = filename.encode("ascii", "replace").decode("ascii") or "file"
    utf_name = quote(filename)
    disposition = "inline" if inline else "attachment"
    mime = file.detected_mime or file.mime_type or "application/octet-stream"
    if inline and (file.extension or "").lower() in {"txt", "csv", "md", "json", "log", "xml", "html", "htm"}:
        mime = "text/plain; charset=utf-8"
    return StreamingResponse(
        iterator(),
        media_type=mime,
        headers={
            "Content-Disposition": f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{utf_name}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
            "Content-Length": str(file.size_bytes),
        },
    )
