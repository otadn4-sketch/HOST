from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db
from app.models.entities import Group, RecoveryToken, User, utcnow
from app.schemas import ResetPasswordIn, UserCreateIn, UserPatchIn
from app.security.passwords import hash_password, validate_password_policy
from app.security.rbac import can_access_admin_panel, can_create_user_with_role, can_manage_users, is_admin
from app.security.sessions import hash_token, new_session_token, revoke_all_user_sessions
from app.services.audit import write_audit
from app.services.files import serialize_user
from app.services.policy import get_or_create_policy

router = APIRouter(prefix="/api/users", tags=["users"])


def _visible_users(db: DBSession, actor: User) -> list[User]:
    q = db.query(User)
    if actor.role == "system_admin":
        return q.order_by(User.created_at.asc()).all()
    if actor.role == "group_admin":
        return q.filter(User.group_id == actor.group_id).order_by(User.created_at.asc()).all()
    return [actor]


@router.get("")
def list_users(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    if not can_access_admin_panel(user) and user.role not in {"user", "viewer"}:
        raise HTTPException(status_code=403, detail="دسترسی ندارید.")
    users = _visible_users(db, user)
    if user.role in {"user", "viewer"}:
        users = [user]
    return {"users": [serialize_user(u) for u in users]}


@router.get("/{user_id}")
def get_user(user_id: str, db: DBSession = Depends(get_db), actor: User = Depends(get_current_user)):
    target = db.query(User).filter(User.id == user_id).one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
    if actor.role == "system_admin" or actor.id == target.id:
        return {"user": serialize_user(target)}
    if actor.role == "group_admin" and target.group_id == actor.group_id:
        return {"user": serialize_user(target)}
    raise HTTPException(status_code=404, detail="کاربر یافت نشد.")


@router.post("")
def create_user(
    payload: UserCreateIn,
    request: Request,
    db: DBSession = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    if not can_create_user_with_role(actor, payload.role):
        raise HTTPException(status_code=403, detail="ایجاد این نقش مجاز نیست.")
    if actor.role == "group_admin":
        payload.group_id = actor.group_id
    if db.query(User).filter(User.username == payload.username).one_or_none():
        raise HTTPException(status_code=409, detail="این نام کاربری قبلاً ثبت شده است.")
    if db.query(User).filter(User.email == payload.email).one_or_none():
        raise HTTPException(status_code=409, detail="این ایمیل قبلاً ثبت شده است.")
    if payload.group_id:
        group = db.query(Group).filter(Group.id == payload.group_id).one_or_none()
        if group is None:
            raise HTTPException(status_code=400, detail="گروه یافت نشد.")
    policy = get_or_create_policy(db)
    err = validate_password_policy(
        payload.password, min_length=policy.password_min_length, require_special=policy.require_special_chars
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    user = User(
        username=payload.username.strip(),
        full_name=payload.full_name.strip(),
        email=payload.email.strip(),
        phone_number=payload.phone_number,
        password_hash=hash_password(payload.password),
        role=payload.role,
        group_id=payload.group_id,
        status=payload.status if payload.status in {"active", "suspended", "pending"} else "active",
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    write_audit(
        db,
        user=actor,
        action="user_created",
        target_resource=user.username,
        target_type="user",
        target_id=user.id,
        details=f"نقش {user.role}",
        request=request,
    )
    return {"user": serialize_user(user)}


@router.patch("/{user_id}")
def patch_user(
    user_id: str,
    payload: UserPatchIn,
    request: Request,
    db: DBSession = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    target = db.query(User).filter(User.id == user_id).one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
    if not can_manage_users(actor, target) and actor.id != target.id:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
    if actor.id == target.id and payload.role and payload.role != target.role:
        raise HTTPException(status_code=403, detail="تغییر نقش خود مجاز نیست.")
    if payload.role and not can_create_user_with_role(actor, payload.role):
        raise HTTPException(status_code=403, detail="این نقش مجاز نیست.")
    if actor.role != "system_admin":
        payload.role = None
        payload.group_id = target.group_id
    if payload.full_name:
        target.full_name = payload.full_name
    if payload.email:
        target.email = payload.email
    if payload.phone_number is not None:
        target.phone_number = payload.phone_number
    if payload.role:
        target.role = payload.role
    if payload.group_id is not None and is_admin(actor):
        target.group_id = payload.group_id
    if payload.status and can_manage_users(actor, target):
        if payload.status not in {"active", "suspended", "pending"}:
            raise HTTPException(status_code=400, detail="وضعیت نامعتبر است.")
        target.status = payload.status
        if payload.status != "active":
            revoke_all_user_sessions(db, target.id)
        write_audit(
            db,
            user=actor,
            action="user_status_changed",
            target_resource=target.username,
            target_type="user",
            target_id=target.id,
            details=f"وضعیت جدید: {payload.status}",
            request=request,
        )
    return {"user": serialize_user(target)}


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: str,
    payload: ResetPasswordIn,
    request: Request,
    db: DBSession = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    target = db.query(User).filter(User.id == user_id).one_or_none()
    if target is None or not can_manage_users(actor, target):
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
    policy = get_or_create_policy(db)
    err = validate_password_policy(
        payload.new_password, min_length=policy.password_min_length, require_special=policy.require_special_chars
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    target.password_hash = hash_password(payload.new_password)
    target.must_change_password = True
    target.failed_login_attempts = 0
    target.locked_until = None
    revoke_all_user_sessions(db, target.id)
    write_audit(
        db,
        user=actor,
        action="password_reset",
        target_resource=target.username,
        target_type="user",
        target_id=target.id,
        details="بازنشانی گذرواژه توسط مدیر",
        severity="warning",
        request=request,
    )
    return {"ok": True}


@router.post("/{user_id}/unlock")
def unlock_user(
    user_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    target = db.query(User).filter(User.id == user_id).one_or_none()
    if target is None or not can_manage_users(actor, target) and not is_admin(actor):
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
    target.failed_login_attempts = 0
    target.locked_until = None
    write_audit(db, user=actor, action="user_status_changed", target_resource=target.username, details="رفع قفل حساب", request=request)
    return {"ok": True}


@router.post("/{user_id}/recovery-token")
def issue_recovery_token(
    user_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    if not is_admin(actor):
        raise HTTPException(status_code=403, detail="فقط مدیر سامانه می‌تواند توکن بازیابی صادر کند.")
    target = db.query(User).filter(User.id == user_id).one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
    token = new_session_token()
    row = RecoveryToken(
        user_id=target.id,
        token_hash=hash_token(token),
        expires_at=utcnow() + timedelta(hours=2),
        created_by=actor.id,
    )
    db.add(row)
    write_audit(
        db,
        user=actor,
        action="password_reset_request",
        target_resource=target.username,
        details="صدور توکن یک‌بارمصرف بازیابی (توکن در پاسخ فقط یک‌بار نمایش داده می‌شود)",
        severity="warning",
        request=request,
    )
    return {"token": token, "expires_at": row.expires_at}
