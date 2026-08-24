from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db
from app.models.entities import MeetingLog, User, utcnow
from app.schemas import MeetingCreateIn
from app.security.rbac import can_upload, is_admin, is_group_admin
from app.services.audit import write_audit
from app.services.phases import require_phase

router = APIRouter(prefix="/api/meetings", tags=["meetings"])

ALLOWED_KINDS = {"physical_meeting", "external_presentation"}


def _visible(user: User, row: MeetingLog) -> bool:
    if is_admin(user):
        return True
    if row.logged_by_user_id == user.id:
        return True
    if is_group_admin(user) and row.group_id and row.group_id == user.group_id:
        return True
    return False


def _serialize(row: MeetingLog, actor: User | None) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "meeting_kind": row.meeting_kind,
        "occurred_at": row.occurred_at,
        "location": row.location,
        "attendees": row.attendees or [],
        "agenda": row.agenda,
        "outcome": row.outcome,
        "notes": row.notes,
        "linked_transaction_id": row.linked_transaction_id,
        "logged_by_user_id": row.logged_by_user_id,
        "logged_by_name": actor.full_name if actor else "",
        "group_id": row.group_id,
        "created_at": row.created_at,
    }


@router.get("")
def list_meetings(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    require_phase("phase_2_meetings_enabled", "فاز ۲ (ثبت جلسات) فعال نیست.")
    rows = (
        db.query(MeetingLog)
        .filter(MeetingLog.is_deleted.is_(False))
        .order_by(MeetingLog.occurred_at.desc())
        .limit(300)
        .all()
    )
    out = []
    for row in rows:
        if not _visible(user, row):
            continue
        actor = db.query(User).filter(User.id == row.logged_by_user_id).one_or_none()
        out.append(_serialize(row, actor))
    return {"meetings": out}


@router.post("")
def create_meeting(
    payload: MeetingCreateIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_phase("phase_2_meetings_enabled", "فاز ۲ (ثبت جلسات) فعال نیست.")
    if not can_upload(user):
        raise HTTPException(status_code=403, detail="مجوز ثبت جلسه ندارید.")
    kind = (payload.meeting_kind or "").strip()
    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=400, detail="نوع جلسه باید جلسه حضوری یا ارائه بیرونی باشد.")
    row = MeetingLog(
        title=payload.title.strip(),
        meeting_kind=kind,
        occurred_at=payload.occurred_at,
        location=(payload.location or "").strip(),
        attendees=payload.attendees or [],
        agenda=(payload.agenda or "").strip(),
        outcome=(payload.outcome or "").strip(),
        notes=(payload.notes or "").strip(),
        linked_transaction_id=payload.linked_transaction_id,
        logged_by_user_id=user.id,
        group_id=user.group_id,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        user=user,
        action="meeting_logged",
        target_resource=row.title,
        target_type="meeting",
        target_id=row.id,
        details=f"ثبت {kind}",
        request=request,
    )
    return {"meeting": _serialize(row, user)}


@router.delete("/{meeting_id}")
def delete_meeting(
    meeting_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_phase("phase_2_meetings_enabled", "فاز ۲ (ثبت جلسات) فعال نیست.")
    row = db.query(MeetingLog).filter(MeetingLog.id == meeting_id, MeetingLog.is_deleted.is_(False)).one_or_none()
    if row is None or not _visible(user, row):
        raise HTTPException(status_code=404, detail="جلسه یافت نشد.")
    if not (is_admin(user) or row.logged_by_user_id == user.id):
        raise HTTPException(status_code=403, detail="حذف این رکورد مجاز نیست.")
    row.is_deleted = True
    row.updated_at = utcnow()
    write_audit(
        db,
        user=user,
        action="meeting_deleted",
        target_resource=row.title,
        target_type="meeting",
        target_id=row.id,
        details="حذف نرم جلسه",
        severity="warning",
        request=request,
    )
    return {"ok": True}
