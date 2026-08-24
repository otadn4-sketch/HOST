from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, Request, UploadFile
from sqlalchemy.orm import Session as DBSession

from app.config import Settings
from app.models.entities import FileObject, FilePermission, Group, OrgRole, User, utcnow
from app.security.rbac import evaluate_file_access, is_admin
from app.services.audit import write_audit
from app.services.file_types import (
    detect_type,
    extension_allowed,
    is_dangerous_extension,
    normalize_extension,
)
from app.services.policy import get_or_create_policy
from app.services.scanner import ClamAVError, scan_file


def vault_abs(settings: Settings, relpath: str) -> Path:
    base = settings.vault_path.resolve()
    target = (settings.vault_path / relpath).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(status_code=400, detail="مسیر نامعتبر")
    return target


def is_malware_hit(file: FileObject) -> bool:
    reason = (file.quarantine_reason or "")
    return file.scan_status == "quarantined" and ("شناسایی بدافزار" in reason or "malware" in reason.lower())


def stored_file_path(settings: Settings, file: FileObject) -> Path:
    try:
        vault = vault_abs(settings, file.storage_relpath)
        if vault.is_file():
            return vault
    except HTTPException:
        pass
    qbase = settings.quarantine_path.resolve()
    qpath = (settings.quarantine_path / file.storage_relpath).resolve()
    if str(qpath).startswith(str(qbase)) and qpath.is_file():
        return qpath
    raise HTTPException(status_code=404, detail="فایل یافت نشد.")


async def stream_to_quarantine(
    upload: UploadFile, dest: Path, max_size: int
) -> tuple[int, str]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    hasher = hashlib.sha256()
    size = 0
    try:
        with dest.open("wb") as fh:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_size:
                    fh.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="حجم فایل از سقف مجاز بیشتر است.")
                hasher.update(chunk)
                fh.write(chunk)
    finally:
        await upload.close()
    return size, hasher.hexdigest()


def ingest_file(
    db: DBSession,
    settings: Settings,
    *,
    user: User,
    request: Request,
    quarantine_path: Path,
    size: int,
    sha256: str,
    original_name: str,
    title: str,
    topic: str,
    group_id: str | None,
    classification: str,
    description: str,
    tags: list[str],
    parent_file_id: str | None,
    permission_specs: list[dict] | None,
) -> FileObject:
    policy = get_or_create_policy(db)
    ext = normalize_extension(original_name)
    group = db.query(Group).filter(Group.id == group_id).one_or_none() if group_id else None
    if group_id and group is None:
        quarantine_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="گروه یافت نشد.")

    max_size = min(policy.max_file_size_bytes, group.max_file_size_bytes if group else policy.max_file_size_bytes)
    if size > max_size:
        quarantine_path.unlink(missing_ok=True)
        raise HTTPException(status_code=413, detail="حجم فایل از سقف مجاز بیشتر است.")

    allowed = list(policy.allowed_extensions or [])
    if group and group.allowed_extensions:
        allowed = [e for e in allowed if e in group.allowed_extensions] or list(group.allowed_extensions)

    detection = detect_type(quarantine_path, original_name)
    stored_name = uuid.uuid4().hex

    dangerous = detection.is_executable or is_dangerous_extension(ext) or is_dangerous_extension(detection.extension)
    if policy.quarantine_dangerous_files and dangerous:
        return _quarantine_record(
            db,
            user,
            request,
            quarantine_path,
            stored_name,
            original_name,
            title,
            topic,
            group,
            classification,
            description,
            tags,
            size,
            sha256,
            detection.mime,
            detection.extension or ext,
            parent_file_id,
            detection.reason or "فایل اجرایی یا خطرناک",
        )

    if detection.reason in {
        "پسوند با نوع واقعی فایل همخوان نیست",
        "ماکرو آفیس شناسایی شد",
        "نوع فایل شناسایی‌نشده است",
        "بسته آسیب‌دیده است",
        "تعداد فایل‌های داخل بسته از حد مجاز بیشتر است",
        "حجم uncompressed بسته بیش از حد مجاز است",
        "نسبت فشرده‌سازی مشکوک (zip bomb)",
        "مسیر غیرمجاز داخل بسته",
        "پیوند نمادین داخل بسته مجاز نیست",
        "بسته تودرتو مجاز نیست",
    }:
        return _quarantine_record(
            db,
            user,
            request,
            quarantine_path,
            stored_name,
            original_name,
            title,
            topic,
            group,
            classification,
            description,
            tags,
            size,
            sha256,
            detection.mime,
            detection.extension or ext,
            parent_file_id,
            detection.reason,
        )

    if not extension_allowed(detection.extension, allowed):
        return _quarantine_record(
            db,
            user,
            request,
            quarantine_path,
            stored_name,
            original_name,
            title,
            topic,
            group,
            classification,
            description,
            tags,
            size,
            sha256,
            detection.mime,
            detection.extension or ext,
            parent_file_id,
            "فرمت فایل در فهرست مجاز نیست",
        )

    scan_status = "clean"
    quarantine_reason = None
    if policy.clamav_enabled and not settings.clamav_disabled:
        try:
            result = scan_file(quarantine_path, settings.clamd_host, settings.clamd_port)
            if not result.clean:
                scan_status = "quarantined"
                quarantine_reason = f"شناسایی بدافزار: {result.signature}"
        except ClamAVError as exc:
            scan_status = "suspicious"
            quarantine_reason = f"پویش بدافزار در دسترس نبود ({exc})"

    if scan_status in {"clean", "suspicious"}:
        rel = stored_name
        dest = settings.vault_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(quarantine_path), str(dest))
        storage_relpath = rel
    else:
        qrel = f"q-{stored_name}"
        dest = settings.quarantine_path / qrel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if quarantine_path != dest:
            shutil.move(str(quarantine_path), str(dest))
        storage_relpath = qrel

    version_number = 1
    version = "v1.0"
    if parent_file_id:
        parent = db.query(FileObject).filter(FileObject.id == parent_file_id, FileObject.is_deleted.is_(False)).one_or_none()
        if parent is None:
            _cleanup(settings, storage_relpath, scan_status)
            raise HTTPException(status_code=404, detail="فایل یافت نشد.")
        access = evaluate_file_access(user, parent, parent.permissions)
        if not access.can_manage:
            _cleanup(settings, storage_relpath, scan_status)
            raise HTTPException(status_code=404, detail="فایل یافت نشد.")
        parent.is_current_version = False
        version_number = parent.version_number + 1
        version = f"v{version_number}.0"
        group = group or db.query(Group).filter(Group.id == parent.group_id).one_or_none()

    file = FileObject(
        title=title or Path(original_name).stem,
        original_name=Path(original_name).name[:300],
        stored_name=stored_name,
        storage_relpath=storage_relpath,
        topic=topic,
        group_id=group.id if group else None,
        uploader_id=user.id,
        size_bytes=size,
        mime_type=detection.mime,
        detected_mime=detection.mime,
        extension=detection.extension or ext,
        classification=classification,
        scan_status=scan_status,
        quarantine_reason=quarantine_reason,
        sha256=sha256,
        description=description,
        version=version,
        version_number=version_number,
        parent_file_id=parent_file_id,
        is_current_version=True,
        tags=tags,
    )
    db.add(file)
    db.flush()
    _apply_default_permissions(db, file, user, group, permission_specs)

    action = "file_upload" if scan_status == "clean" else "file_quarantined"
    write_audit(
        db,
        user=user,
        action=action,
        target_resource=file.title,
        target_type="file",
        target_id=file.id,
        details=quarantine_reason or "بارگذاری و پویش تکمیل شد.",
        severity="critical" if scan_status != "clean" else "info",
        request=request,
    )
    return file


def _cleanup(settings: Settings, relpath: str, scan_status: str) -> None:
    base = settings.vault_path if scan_status in {"clean", "suspicious"} else settings.quarantine_path
    path = (base / relpath)
    path.unlink(missing_ok=True)


def _quarantine_record(
    db,
    user,
    request,
    quarantine_path,
    stored_name,
    original_name,
    title,
    topic,
    group,
    classification,
    description,
    tags,
    size,
    sha256,
    mime,
    ext,
    parent_file_id,
    reason,
) -> FileObject:
    qrel = f"q-{stored_name}"
    dest = Path(quarantine_path).parent / qrel
    if Path(quarantine_path) != dest:
        shutil.move(str(quarantine_path), str(dest))
    file = FileObject(
        title=title or Path(original_name).stem,
        original_name=Path(original_name).name[:300],
        stored_name=stored_name,
        storage_relpath=qrel,
        topic=topic,
        group_id=group.id if group else None,
        uploader_id=user.id,
        size_bytes=size,
        mime_type=mime,
        detected_mime=mime,
        extension=ext,
        classification=classification,
        scan_status="quarantined",
        quarantine_reason=reason,
        sha256=sha256,
        description=description,
        parent_file_id=parent_file_id,
        tags=tags,
    )
    db.add(file)
    db.flush()
    write_audit(
        db,
        user=user,
        action="file_quarantined",
        target_resource=file.title,
        target_type="file",
        target_id=file.id,
        details=reason,
        severity="critical",
        request=request,
    )
    return file


def _apply_default_permissions(db, file: FileObject, user: User, group: Group | None, specs: list[dict] | None) -> None:
    db.add(
        FilePermission(
            file_id=file.id,
            target_type="user",
            target_id=user.id,
            can_view=True,
            can_download=True,
            can_upload=True,
            can_manage=True,
            granted_by=user.id,
        )
    )
    if group and file.classification in {"public", "internal"}:
        db.add(
            FilePermission(
                file_id=file.id,
                target_type="group",
                target_id=group.id,
                can_view=True,
                can_download=True,
                can_upload=False,
                can_manage=False,
                granted_by=user.id,
            )
        )
    if specs:
        for spec in specs:
            db.add(
                FilePermission(
                    file_id=file.id,
                    target_type=spec["target_type"],
                    target_id=spec["target_id"],
                    can_view=spec.get("can_view", True),
                    can_download=spec.get("can_download", False),
                    can_upload=spec.get("can_upload", False),
                    can_manage=spec.get("can_manage", False),
                    granted_by=user.id,
                )
            )


def serialize_file(db: DBSession, file: FileObject, user: User) -> dict:
    group = db.query(Group).filter(Group.id == file.group_id).one_or_none() if file.group_id else None
    uploader = db.query(User).filter(User.id == file.uploader_id).one_or_none()
    access = evaluate_file_access(user, file, file.permissions)
    admin = is_admin(user)
    payload = {
        "id": file.id,
        "title": file.title,
        "original_name": file.original_name,
        "stored_vault_name": file.stored_name if admin else "",
        "topic": file.topic,
        "department_id": file.group_id,
        "department_name": group.name if group else "",
        "uploader_id": file.uploader_id,
        "uploader_name": uploader.full_name if uploader else "",
        "size_bytes": file.size_bytes,
        "mime_type": file.mime_type,
        "extension": file.extension,
        "version": file.version,
        "version_number": file.version_number,
        "parent_file_id": file.parent_file_id,
        "classification": file.classification,
        "scan_status": file.scan_status,
        "quarantine_reason": file.quarantine_reason if admin else None,
        "download_count": file.download_count,
        "view_count": file.view_count,
        "tags": file.tags or [],
        "authors": getattr(file, "authors", None) or [],
        "excel_logged": getattr(file, "excel_logged", None) or {} if admin else {},
        "faran_remote_id": getattr(file, "faran_remote_id", None) if admin else None,
        "created_at": file.created_at,
        "updated_at": file.updated_at,
        "checksum_sha256": file.sha256 if admin else "",
        "description": file.description,
        "can_download": access.can_download,
        "can_manage": access.can_manage,
        "permissions": [
            {
                "id": p.id,
                "target_type": p.target_type,
                "target_id": p.target_id,
                "can_view": p.can_view,
                "can_download": p.can_download,
                "can_upload": p.can_upload,
                "can_manage": p.can_manage,
            }
            for p in file.permissions
        ]
        if access.can_manage or admin
        else [],
    }
    return payload


def serialize_user(user: User, group: Group | None = None) -> dict:
    group = group or user.group
    last = user.last_login_at.isoformat() if user.last_login_at else None
    org_role = user.org_role
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": user.role,
        "org_role_id": user.org_role_id,
        "org_role_name": org_role.name if org_role else "",
        "group_id": user.group_id,
        "department_id": user.group_id,
        "department_name": group.name if group else "",
        "status": user.status,
        "last_login": last,
        "created_at": user.created_at,
        "must_change_password": user.must_change_password,
    }


def serialize_role(role: "OrgRole", members_count: int = 0) -> dict:
    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "permission_level": role.permission_level,
        "is_system": role.is_system,
        "is_active": role.is_active,
        "members_count": members_count,
    }


def serialize_group(group: Group, members_count: int, manager_name: str = "") -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "code": group.code,
        "description": group.description,
        "manager_id": group.manager_id,
        "manager_name": manager_name,
        "members_count": members_count,
        "allowed_file_extensions": group.allowed_extensions or [],
        "max_file_size_mb": max(1, group.max_file_size_bytes // (1024 * 1024)),
        "default_classification": group.default_classification,
        "is_active": group.is_active,
    }


def get_visible_file(db: DBSession, user: User, file_id: str) -> tuple[FileObject | None, object]:
    file = db.query(FileObject).filter(FileObject.id == file_id, FileObject.is_deleted.is_(False)).one_or_none()
    if file is None:
        return None, None
    access = evaluate_file_access(user, file, file.permissions)
    if not access.can_view:
        return None, None
    return file, access
