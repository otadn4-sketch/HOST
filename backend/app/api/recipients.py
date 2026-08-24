from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db
from app.models.entities import ExternalRecipient, InteractionTransaction, User, utcnow
from app.schemas import RecipientCreateIn, RecipientPatchIn
from app.security.rbac import can_upload, is_admin, is_group_admin
from app.services.audit import write_audit
from app.services.phases import require_phase

router = APIRouter(prefix="/api/recipients", tags=["recipients"])


def _can_see(user: User, row: ExternalRecipient) -> bool:
    if is_admin(user):
        return True
    if row.created_by == user.id:
        return True
    if is_group_admin(user) and row.group_id and row.group_id == user.group_id:
        return True
    return False


def _serialize(db: DBSession, row: ExternalRecipient, *, include_history: bool) -> dict:
    payload = {
        "id": row.id,
        "full_name": row.full_name,
        "organization": row.organization,
        "title": row.title,
        "email": row.email,
        "phone": row.phone,
        "request_origin": row.request_origin,
        "source": row.source,
        "notes": row.notes,
        "tags": row.tags or [],
        "is_active": row.is_active,
        "created_by": row.created_by,
        "group_id": row.group_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
    if include_history:
        txs = (
            db.query(InteractionTransaction)
            .filter(
                InteractionTransaction.recipient_id == row.id,
                InteractionTransaction.is_deleted.is_(False),
            )
            .order_by(InteractionTransaction.occurred_at.desc())
            .limit(100)
            .all()
        )
        payload["history"] = [
            {
                "id": tx.id,
                "kind": tx.kind,
                "file_id": tx.file_id,
                "occurred_at": tx.occurred_at,
                "purpose": tx.purpose,
                "channel": tx.channel,
            }
            for tx in txs
        ]
    return payload


@router.get("")
def list_recipients(
    q: str = "",
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_phase("phase_1_archive_enabled", "فاز ۱ فعال نیست.")
    rows = db.query(ExternalRecipient).filter(ExternalRecipient.is_active.is_(True)).order_by(ExternalRecipient.full_name.asc()).all()
    needle = q.strip().lower()
    result = []
    for row in rows:
        if not _can_see(user, row):
            continue
        blob = f"{row.full_name} {row.organization} {row.request_origin}".lower()
        if needle and needle not in blob:
            continue
        result.append(_serialize(db, row, include_history=False))
    return {"recipients": result}


@router.post("")
def create_recipient(
    payload: RecipientCreateIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_phase("phase_1_archive_enabled", "فاز ۱ فعال نیست.")
    if not can_upload(user):
        raise HTTPException(status_code=403, detail="مجوز ایجاد مخاطب ندارید.")
    row = ExternalRecipient(
        full_name=payload.full_name.strip(),
        organization=(payload.organization or "").strip(),
        title=(payload.title or "").strip(),
        email=(payload.email or "").strip(),
        phone=(payload.phone or "").strip(),
        request_origin=(payload.request_origin or "").strip(),
        source="manual",
        notes=(payload.notes or "").strip(),
        tags=payload.tags or [],
        created_by=user.id,
        group_id=user.group_id,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        user=user,
        action="recipient_created",
        target_resource=row.full_name,
        target_type="recipient",
        target_id=row.id,
        details="ایجاد مخاطب بیرونی",
        request=request,
    )
    return {"recipient": _serialize(db, row, include_history=False)}


@router.get("/{recipient_id}")
def get_recipient(
    recipient_id: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_phase("phase_3_recipient_profiles_enabled", "فاز ۳ (پروفایل مخاطبان) فعال نیست.")
    row = db.query(ExternalRecipient).filter(ExternalRecipient.id == recipient_id).one_or_none()
    if row is None or not _can_see(user, row):
        raise HTTPException(status_code=404, detail="مخاطب یافت نشد.")
    return {"recipient": _serialize(db, row, include_history=True)}


@router.patch("/{recipient_id}")
def patch_recipient(
    recipient_id: str,
    payload: RecipientPatchIn,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_phase("phase_3_recipient_profiles_enabled", "فاز ۳ (پروفایل مخاطبان) فعال نیست.")
    row = db.query(ExternalRecipient).filter(ExternalRecipient.id == recipient_id).one_or_none()
    if row is None or not _can_see(user, row):
        raise HTTPException(status_code=404, detail="مخاطب یافت نشد.")
    if not (is_admin(user) or row.created_by == user.id):
        raise HTTPException(status_code=403, detail="ویرایش این مخاطب مجاز نیست.")
    for field in ("full_name", "organization", "title", "email", "phone", "request_origin", "notes"):
        value = getattr(payload, field)
        if value is not None:
            setattr(row, field, value.strip() if isinstance(value, str) else value)
    if payload.tags is not None:
        row.tags = payload.tags
    if payload.is_active is not None and is_admin(user):
        row.is_active = payload.is_active
    row.updated_at = utcnow()
    return {"recipient": _serialize(db, row, include_history=False)}
