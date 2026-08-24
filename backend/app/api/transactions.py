from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db
from app.models.entities import ExternalRecipient, FileObject, InteractionTransaction, User, utcnow
from app.schemas import TransactionCreateIn, TransactionPatchIn
from app.security.rbac import can_upload, evaluate_file_access, is_admin, is_group_admin
from app.services.audit import write_audit
from app.services.phases import require_phase

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

ALLOWED_CHANNELS = {"handoff", "email_offline", "physical_media", "other"}
BLOCKED_CHANNELS = {"sms", "telegram", "whatsapp", "messenger", "auto", "automated", "bot"}
ALLOWED_KINDS = {"file_delivery", "other"}


def _visible(user: User, row: InteractionTransaction, file: FileObject | None) -> bool:
    if is_admin(user):
        return True
    if row.logged_by_user_id == user.id:
        return True
    if is_group_admin(user) and row.group_id and row.group_id == user.group_id:
        return True
    if file is not None:
        access = evaluate_file_access(user, file, file.permissions)
        return bool(access.can_view)
    return False


def _serialize(db: DBSession, row: InteractionTransaction) -> dict:
    file = db.query(FileObject).filter(FileObject.id == row.file_id).one_or_none() if row.file_id else None
    actor = db.query(User).filter(User.id == row.logged_by_user_id).one_or_none()
    recipient = (
        db.query(ExternalRecipient).filter(ExternalRecipient.id == row.recipient_id).one_or_none()
        if row.recipient_id
        else None
    )
    return {
        "id": row.id,
        "kind": row.kind,
        "file_id": row.file_id,
        "file_title": file.title if file else "",
        "recipient_id": row.recipient_id,
        "recipient_name": row.recipient_name,
        "recipient_organization": row.recipient_organization,
        "recipient_origin": recipient.request_origin if recipient else "",
        "occurred_at": row.occurred_at,
        "purpose": row.purpose,
        "channel": row.channel,
        "notes": row.notes,
        "logged_by_user_id": row.logged_by_user_id,
        "logged_by_name": actor.full_name if actor else "",
        "group_id": row.group_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "automated": False,
    }


def _get_file(db: DBSession, user: User, file_id: str | None) -> FileObject | None:
    if not file_id:
        return None
    file = db.query(FileObject).filter(FileObject.id == file_id, FileObject.is_deleted.is_(False)).one_or_none()
    if file is None:
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    access = evaluate_file_access(user, file, file.permissions)
    if not access.can_view:
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    return file


@router.get("")
def list_transactions(
    q: str = "",
    file_id: str | None = None,
    recipient: str | None = None,
    purpose: str | None = None,
    channel: str | None = None,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_phase("phase_1_archive_enabled", "فاز ۱ (بایگانی و ثبت دستی) فعال نیست.")
    query = db.query(InteractionTransaction).filter(InteractionTransaction.is_deleted.is_(False))
    if file_id:
        query = query.filter(InteractionTransaction.file_id == file_id)
    if date_from:
        query = query.filter(InteractionTransaction.occurred_at >= date_from)
    if date_to:
        query = query.filter(InteractionTransaction.occurred_at <= date_to)
    if channel:
        query = query.filter(InteractionTransaction.channel == channel)
    rows = query.order_by(InteractionTransaction.occurred_at.desc()).limit(500).all()
    result = []
    needle = (q or "").strip().lower()
    rec_needle = (recipient or "").strip().lower()
    purpose_needle = (purpose or "").strip().lower()
    for row in rows:
        file = db.query(FileObject).filter(FileObject.id == row.file_id).one_or_none() if row.file_id else None
        if not _visible(user, row, file):
            continue
        blob = " ".join(
            [
                row.recipient_name or "",
                row.recipient_organization or "",
                row.purpose or "",
                row.notes or "",
                file.title if file else "",
            ]
        ).lower()
        if needle and needle not in blob:
            continue
        if rec_needle and rec_needle not in f"{row.recipient_name} {row.recipient_organization}".lower():
            continue
        if purpose_needle and purpose_needle not in (row.purpose or "").lower():
            continue
        result.append(_serialize(db, row))
    return {"transactions": result, "automated_delivery_enabled": False}


@router.post("")
def create_transaction(
    payload: TransactionCreateIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_phase("phase_1_archive_enabled", "فاز ۱ (بایگانی و ثبت دستی) فعال نیست.")
    if not can_upload(user):
        raise HTTPException(status_code=403, detail="مجوز ثبت تراکنش ندارید.")
    channel = (payload.channel or "handoff").strip().lower()
    if channel in BLOCKED_CHANNELS or channel not in ALLOWED_CHANNELS:
        raise HTTPException(
            status_code=400,
            detail="کانال ارسال خودکار (پیامک/پیام‌رسان) مجاز نیست. فقط ثبت دستی تحویل حضوری، رایانامه خارج از سامانه، رسانه فیزیکی یا سایر روش‌های غیرخودکار ممکن است.",
        )
    kind = (payload.kind or "file_delivery").strip()
    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=400, detail="نوع تراکنش نامعتبر است.")
    file = _get_file(db, user, payload.file_id)
    recipient_id = payload.recipient_id
    recipient_name = payload.recipient_name.strip()
    recipient_org = (payload.recipient_organization or "").strip()
    if recipient_id:
        rec = db.query(ExternalRecipient).filter(ExternalRecipient.id == recipient_id, ExternalRecipient.is_active.is_(True)).one_or_none()
        if rec is None:
            raise HTTPException(status_code=404, detail="مخاطب یافت نشد.")
        recipient_name = rec.full_name
        recipient_org = rec.organization or recipient_org
    elif payload.create_recipient:
        rec = ExternalRecipient(
            full_name=recipient_name,
            organization=recipient_org,
            request_origin=(payload.request_origin or "").strip(),
            source="manual",
            created_by=user.id,
            group_id=user.group_id,
        )
        db.add(rec)
        db.flush()
        recipient_id = rec.id
    row = InteractionTransaction(
        kind=kind,
        file_id=file.id if file else None,
        recipient_id=recipient_id,
        recipient_name=recipient_name,
        recipient_organization=recipient_org,
        occurred_at=payload.occurred_at,
        purpose=payload.purpose.strip(),
        channel=channel,
        notes=(payload.notes or "").strip(),
        logged_by_user_id=user.id,
        group_id=user.group_id,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        user=user,
        action="transaction_logged",
        target_resource=recipient_name,
        target_type="transaction",
        target_id=row.id,
        details=f"ثبت دستی تحویل؛ کانال={channel}؛ هدف={payload.purpose.strip()[:120]}",
        request=request,
    )
    return {"transaction": _serialize(db, row)}


@router.get("/{transaction_id}")
def get_transaction(
    transaction_id: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_phase("phase_1_archive_enabled", "فاز ۱ (بایگانی و ثبت دستی) فعال نیست.")
    row = (
        db.query(InteractionTransaction)
        .filter(InteractionTransaction.id == transaction_id, InteractionTransaction.is_deleted.is_(False))
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="تراکنش یافت نشد.")
    file = db.query(FileObject).filter(FileObject.id == row.file_id).one_or_none() if row.file_id else None
    if not _visible(user, row, file):
        raise HTTPException(status_code=404, detail="تراکنش یافت نشد.")
    return {"transaction": _serialize(db, row)}


@router.patch("/{transaction_id}")
def patch_transaction(
    transaction_id: str,
    payload: TransactionPatchIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_phase("phase_1_archive_enabled", "فاز ۱ (بایگانی و ثبت دستی) فعال نیست.")
    row = (
        db.query(InteractionTransaction)
        .filter(InteractionTransaction.id == transaction_id, InteractionTransaction.is_deleted.is_(False))
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="تراکنش یافت نشد.")
    if not (is_admin(user) or row.logged_by_user_id == user.id):
        raise HTTPException(status_code=403, detail="فقط ثبت‌کننده یا مدیر سامانه می‌تواند این رکورد را ویرایش کند.")
    if payload.channel is not None:
        channel = payload.channel.strip().lower()
        if channel in BLOCKED_CHANNELS or channel not in ALLOWED_CHANNELS:
            raise HTTPException(status_code=400, detail="کانال ارسال خودکار مجاز نیست.")
        row.channel = channel
    if payload.purpose is not None:
        row.purpose = payload.purpose.strip()
    if payload.notes is not None:
        row.notes = payload.notes.strip()
    if payload.occurred_at is not None:
        row.occurred_at = payload.occurred_at
    if payload.recipient_name is not None:
        row.recipient_name = payload.recipient_name.strip()
    if payload.recipient_organization is not None:
        row.recipient_organization = payload.recipient_organization.strip()
    row.updated_at = utcnow()
    write_audit(
        db,
        user=user,
        action="transaction_updated",
        target_resource=row.recipient_name,
        target_type="transaction",
        target_id=row.id,
        details="ویرایش ثبت دستی تراکنش",
        request=request,
    )
    return {"transaction": _serialize(db, row)}


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_phase("phase_1_archive_enabled", "فاز ۱ (بایگانی و ثبت دستی) فعال نیست.")
    row = (
        db.query(InteractionTransaction)
        .filter(InteractionTransaction.id == transaction_id, InteractionTransaction.is_deleted.is_(False))
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="تراکنش یافت نشد.")
    if not (is_admin(user) or row.logged_by_user_id == user.id):
        raise HTTPException(status_code=403, detail="حذف این رکورد مجاز نیست.")
    row.is_deleted = True
    row.updated_at = utcnow()
    write_audit(
        db,
        user=user,
        action="transaction_deleted",
        target_resource=row.recipient_name,
        target_type="transaction",
        target_id=row.id,
        details="حذف نرم ثبت دستی تراکنش",
        severity="warning",
        request=request,
    )
    return {"ok": True}
