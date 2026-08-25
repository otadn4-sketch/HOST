from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db
from app.api.files import _stream_file
from app.config import Settings, get_settings
from app.models.entities import FileObject, ShareLink, User, aware, utcnow
from app.schemas import ShareCreateIn
from app.security.rbac import can_upload, evaluate_file_access, is_admin
from app.services.audit import write_audit
from app.services.files import is_malware_hit, stored_file_path
from app.services.phases import require_phase

router = APIRouter(prefix="/api/shares", tags=["shares"])

PHASE_OFF = "فاز ۴ (اشتراک‌گذاری درون‌شبکه‌ای) فعال نیست."
PUBLIC_DENIED = "اشتراک عمومی یا ناشناس مجاز نیست. فقط کاربر مشخص داخل سامانه می‌تواند گیرنده باشد."


def _require_phase() -> None:
    require_phase("phase_4_sharing_enabled", PHASE_OFF)


def _expired(row: ShareLink) -> bool:
    if row.expires_at is None:
        return False
    exp = aware(row.expires_at)
    return bool(exp and exp <= datetime.now(timezone.utc))


def _usable(row: ShareLink) -> bool:
    if not row.is_active or row.revoked_at is not None:
        return False
    if _expired(row):
        return False
    if row.max_downloads and row.download_count >= row.max_downloads:
        return False
    return True


def _can_see_share(user: User, row: ShareLink) -> bool:
    if is_admin(user):
        return True
    return user.id in {row.created_by, row.grantee_user_id}


def _serialize(db: DBSession, row: ShareLink) -> dict:
    file = db.query(FileObject).filter(FileObject.id == row.file_id).one_or_none()
    grantee = db.query(User).filter(User.id == row.grantee_user_id).one_or_none() if row.grantee_user_id else None
    creator = db.query(User).filter(User.id == row.created_by).one_or_none()
    return {
        "id": row.id,
        "file_id": row.file_id,
        "file_title": file.title if file else "",
        "grantee_user_id": row.grantee_user_id,
        "grantee_name": grantee.full_name if grantee else "",
        "created_by": row.created_by,
        "created_by_name": creator.full_name if creator else "",
        "audience": "internal",
        "can_view": bool(row.can_view),
        "can_download": bool(row.can_download),
        "expires_at": row.expires_at,
        "max_downloads": row.max_downloads,
        "download_count": row.download_count,
        "is_active": bool(row.is_active) and row.revoked_at is None and not _expired(row),
        "revoked_at": row.revoked_at,
        "purpose": row.purpose or "",
        "created_at": row.created_at,
        "public": False,
        "anonymous": False,
    }


@router.get("")
def list_shares(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    _require_phase()
    query = db.query(ShareLink)
    if not is_admin(user):
        query = query.filter(or_(ShareLink.created_by == user.id, ShareLink.grantee_user_id == user.id))
    rows = query.order_by(ShareLink.created_at.desc()).limit(300).all()
    return {"shares": [_serialize(db, row) for row in rows], "public_links": False}


@router.get("/directory")
def share_directory(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    _require_phase()
    if not can_upload(user):
        raise HTTPException(status_code=403, detail="مشاهده‌گر نمی‌تواند اشتراک ایجاد کند.")
    users = db.query(User).filter(User.status == "active").order_by(User.full_name.asc()).all()
    if not is_admin(user):
        users = [item for item in users if item.group_id == user.group_id]
    return {
        "users": [
            {"id": item.id, "full_name": item.full_name, "role": item.role, "username": item.username}
            for item in users
            if item.id != user.id
        ]
    }


@router.post("")
def create_share(
    payload: ShareCreateIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_phase()
    if not can_upload(user):
        raise HTTPException(status_code=403, detail="نقش شما اجازه ایجاد اشتراک ندارد.")
    audience = (payload.audience or "internal").strip().lower()
    if audience in {"public", "anonymous", "external", "open"}:
        raise HTTPException(status_code=400, detail=PUBLIC_DENIED)
    if audience != "internal":
        raise HTTPException(status_code=400, detail=PUBLIC_DENIED)
    if not payload.grantee_user_id:
        raise HTTPException(status_code=400, detail="گیرندهٔ اشتراک باید یک کاربر داخل سامانه باشد.")
    file = db.query(FileObject).filter(FileObject.id == payload.file_id, FileObject.is_deleted.is_(False)).one_or_none()
    if file is None:
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    access = evaluate_file_access(user, file, file.permissions)
    if not access.can_manage:
        raise HTTPException(status_code=403, detail="برای اشتراک این فایل مجوز مدیریت لازم است.")
    if file.scan_status != "clean":
        raise HTTPException(status_code=400, detail="فقط فایل پویش‌شده و پاک قابل اشتراک است.")
    grantee = db.query(User).filter(User.id == payload.grantee_user_id, User.status == "active").one_or_none()
    if grantee is None:
        raise HTTPException(status_code=404, detail="کاربر گیرنده یافت نشد.")
    if grantee.id == user.id:
        raise HTTPException(status_code=400, detail="اشتراک با خودتان لازم نیست.")
    if not is_admin(user) and user.group_id and grantee.group_id != user.group_id:
        raise HTTPException(status_code=403, detail="فقط می‌توانید با کاربران واحد خودتان اشتراک بگذارید.")
    expires = aware(payload.expires_at) if payload.expires_at else None
    if expires and expires <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="تاریخ انقضا باید در آینده باشد.")
    token_hash = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
    row = ShareLink(
        file_id=file.id,
        token_hash=token_hash,
        audience="internal",
        grantee_user_id=grantee.id,
        can_view=True,
        can_download=bool(payload.can_download),
        expires_at=expires,
        max_downloads=max(0, int(payload.max_downloads or 0)),
        download_count=0,
        is_active=True,
        created_by=user.id,
        purpose=(payload.purpose or "").strip()[:500],
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        user=user,
        action="share_created",
        target_resource=file.title,
        target_type="share",
        target_id=row.id,
        details=f"اشتراک درون‌شبکه‌ای برای {grantee.full_name}",
        request=request,
    )
    return {"share": _serialize(db, row)}


@router.get("/{share_id}")
def get_share(share_id: str, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    _require_phase()
    row = db.query(ShareLink).filter(ShareLink.id == share_id).one_or_none()
    if row is None or not _can_see_share(user, row):
        raise HTTPException(status_code=404, detail="اشتراک یافت نشد.")
    return {"share": _serialize(db, row)}


@router.post("/{share_id}/revoke")
def revoke_share(
    share_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_phase()
    row = db.query(ShareLink).filter(ShareLink.id == share_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="اشتراک یافت نشد.")
    if not (is_admin(user) or row.created_by == user.id):
        raise HTTPException(status_code=404, detail="اشتراک یافت نشد.")
    row.is_active = False
    row.revoked_at = utcnow()
    write_audit(
        db,
        user=user,
        action="share_revoked",
        target_resource=row.id,
        target_type="share",
        target_id=row.id,
        details="لغو اشتراک درون‌شبکه‌ای",
        severity="warning",
        request=request,
    )
    return {"share": _serialize(db, row)}


@router.get("/{share_id}/download")
def download_shared_file(
    share_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    _require_phase()
    row = db.query(ShareLink).filter(ShareLink.id == share_id).one_or_none()
    if row is None or not _can_see_share(user, row):
        write_audit(
            db,
            user=user,
            action="suspicious_activity",
            target_resource=share_id,
            details="تلاش غیرمجاز برای دریافت فایل از مسیر اشتراک",
            severity="warning",
            request=request,
            target_type="share",
            target_id=share_id,
        )
        raise HTTPException(status_code=404, detail="اشتراک یافت نشد.")
    if user.id != row.grantee_user_id and not is_admin(user):
        raise HTTPException(status_code=404, detail="اشتراک یافت نشد.")
    if not _usable(row):
        raise HTTPException(status_code=403, detail="این اشتراک منقضی، لغو یا غیرفعال است.")
    if not row.can_download:
        raise HTTPException(status_code=403, detail="این اشتراک اجازهٔ دریافت فایل ندارد.")
    file = db.query(FileObject).filter(FileObject.id == row.file_id, FileObject.is_deleted.is_(False)).one_or_none()
    if file is None:
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    access = evaluate_file_access(user, file, file.permissions)
    if is_malware_hit(file) or file.scan_status != "clean":
        raise HTTPException(status_code=403, detail="فایل قرنطینه یا مشکوک از مسیر اشتراک قابل دریافت نیست.")
    if not (access.can_download or row.can_download):
        raise HTTPException(status_code=403, detail="مجوز دریافت این فایل برقرار نیست.")
    path = stored_file_path(settings, file)
    row.download_count += 1
    file.download_count += 1
    write_audit(
        db,
        user=user,
        action="share_download",
        target_resource=file.title,
        target_type="file",
        target_id=file.id,
        details="دریافت از مسیر اشتراک درون‌شبکه‌ای با کنترل مجدد مجوز فایل",
        request=request,
    )
    return _stream_file(file, path, inline=False)
