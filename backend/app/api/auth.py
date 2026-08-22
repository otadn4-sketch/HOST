from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session as DBSession

from app.config import Settings, get_settings
from app.models.entities import RecoveryToken, User, utcnow
from app.api.deps import get_current_user, get_db
from app.schemas import ChangePasswordRequest, LoginRequest, RecoveryConfirmIn, RecoveryRequestIn
from app.security.passwords import dummy_verify, hash_password, validate_password_policy, verify_password
from app.security.rate_limit import limiter
from app.security.sessions import (
    create_session,
    hash_token,
    new_session_token,
    revoke_all_user_sessions,
    revoke_session,
)
from app.services.audit import write_audit
from app.services.files import serialize_user
from app.services.policy import get_or_create_policy

router = APIRouter(prefix="/api/auth", tags=["auth"])

GENERIC_LOGIN_ERROR = "نام کاربری یا گذرواژه نادرست است."


def _set_session_cookies(response: Response, settings: Settings, token: str, csrf: str, timeout_minutes: int) -> None:
    max_age = timeout_minutes * 60
    secure = settings.is_production
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf,
        max_age=max_age,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def _clear_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


@router.get("/csrf")
def csrf_bootstrap(request: Request, settings: Settings = Depends(get_settings)):
    token = request.cookies.get(settings.csrf_cookie_name) or ""
    return {"csrf_token": token}


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DBSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    ip = request.client.host if request.client else "unknown"
    if not limiter.allow(f"login-ip:{ip}", limit=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="تعداد تلاش‌ها بیش از حد مجاز است. بعداً دوباره تلاش کنید.")
    if not limiter.allow(f"login-user:{payload.username.lower()}", limit=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="تعداد تلاش‌ها بیش از حد مجاز است. بعداً دوباره تلاش کنید.")

    policy = get_or_create_policy(db)
    user = db.query(User).filter(User.username == payload.username).one_or_none()
    now = utcnow()

    if user is None:
        dummy_verify(payload.password)
        write_audit(
            db,
            user=None,
            action="login_failed",
            target_resource="درگاه ورود",
            details="تلاش ورود با شناسه نامعتبر",
            severity="warning",
            request=request,
            username_override=payload.username[:80],
        )
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN_ERROR)

    locked_until = user.locked_until
    if locked_until is not None and locked_until.tzinfo is None:
        from datetime import timezone as tz

        locked_until = locked_until.replace(tzinfo=tz.utc)
    if locked_until and locked_until > now:
        write_audit(
            db,
            user=user,
            action="login_failed",
            target_resource="درگاه ورود",
            details="تلاش ورود در زمان قفل حساب",
            severity="warning",
            request=request,
        )
        raise HTTPException(status_code=423, detail="حساب به‌صورت موقت قفل شده است. بعداً تلاش کنید.")

    if user.status != "active":
        dummy_verify(payload.password)
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN_ERROR)

    if not verify_password(payload.password, user.password_hash):
        user.failed_login_attempts += 1
        remaining = max(0, policy.max_failed_login_attempts - user.failed_login_attempts)
        if user.failed_login_attempts >= policy.max_failed_login_attempts:
            user.locked_until = now + timedelta(minutes=policy.lockout_duration_minutes)
            write_audit(
                db,
                user=user,
                action="account_locked",
                target_resource=user.username,
                details=f"قفل موقت به مدت {policy.lockout_duration_minutes} دقیقه پس از تلاش‌های ناموفق",
                severity="critical",
                request=request,
            )
        write_audit(
            db,
            user=user,
            action="login_failed",
            target_resource="درگاه ورود",
            details=f"گذرواژه نادرست (باقیمانده: {remaining})",
            severity="warning",
            request=request,
        )
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN_ERROR)

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    session, token = create_session(
        db,
        user,
        timeout_minutes=policy.session_timeout_minutes,
        ip=ip,
        user_agent=request.headers.get("user-agent", ""),
    )
    write_audit(
        db,
        user=user,
        action="login_success",
        target_resource="درگاه ورود",
        details="ورود موفق",
        request=request,
    )
    _set_session_cookies(response, settings, token, session.csrf_secret, policy.session_timeout_minutes)
    return {"user": serialize_user(user), "csrf_token": session.csrf_secret}


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: DBSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
):
    session = getattr(request.state, "session", None)
    if session:
        revoke_session(session)
    write_audit(db, user=user, action="logout", target_resource="خروج", details="خروج امن نشست", request=request)
    _clear_cookies(response, settings)
    return {"ok": True}


@router.get("/me")
def me(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    db: DBSession = Depends(get_db),
):
    policy = get_or_create_policy(db)
    session = request.state.session
    _set_session_cookies(response, settings, request.cookies.get(settings.session_cookie_name, ""), session.csrf_secret, policy.session_timeout_minutes)
    from app.models.entities import MaintenanceState

    maint = db.query(MaintenanceState).filter(MaintenanceState.id == 1).one_or_none()
    return {
        "user": serialize_user(user),
        "csrf_token": session.csrf_secret,
        "maintenance": bool(maint and maint.enabled),
    }


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    policy = get_or_create_policy(db)
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="گذرواژه فعلی نادرست است.")
    err = validate_password_policy(
        payload.new_password, min_length=policy.password_min_length, require_special=policy.require_special_chars
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.password_changed_at = utcnow()
    revoke_all_user_sessions(db, user.id)
    write_audit(db, user=user, action="password_reset", target_resource=user.username, details="تغییر گذرواژه توسط خود کاربر", request=request)
    return {"ok": True, "relogin_required": True}


@router.post("/recovery/request")
def recovery_request(
    payload: RecoveryRequestIn,
    request: Request,
    db: DBSession = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    if not limiter.allow(f"recovery:{ip}", limit=5, window_seconds=300):
        raise HTTPException(status_code=429, detail="تعداد درخواست بازیابی بیش از حد مجاز است.")
    user = db.query(User).filter(User.username == payload.username).one_or_none()
    write_audit(
        db,
        user=user,
        action="password_reset_request",
        target_resource="بازیابی دسترسی",
        details="درخواست بازیابی دسترسی ثبت شد و نیازمند اقدام مدیر سامانه است.",
        severity="warning",
        request=request,
        username_override=payload.username[:80],
    )
    return {
        "ok": True,
        "message": "اگر حساب وجود داشته باشد، درخواست بازیابی برای مدیر سامانه ثبت شد. بازیابی برون‌خط و از طریق مدیر انجام می‌شود.",
    }


@router.post("/recovery/confirm")
def recovery_confirm(
    payload: RecoveryConfirmIn,
    request: Request,
    db: DBSession = Depends(get_db),
):
    policy = get_or_create_policy(db)
    row = db.query(RecoveryToken).filter(RecoveryToken.token_hash == hash_token(payload.token)).one_or_none()
    now = utcnow()
    if row is None or row.used_at is not None or row.expires_at < now:
        raise HTTPException(status_code=400, detail="توکن بازیابی نامعتبر یا منقضی است.")
    err = validate_password_policy(
        payload.new_password, min_length=policy.password_min_length, require_special=policy.require_special_chars
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    user = db.query(User).filter(User.id == row.user_id).one()
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.failed_login_attempts = 0
    user.locked_until = None
    row.used_at = now
    revoke_all_user_sessions(db, user.id)
    write_audit(db, user=user, action="password_reset", target_resource=user.username, details="بازیابی دسترسی با توکن یک‌بارمصرف", request=request)
    return {"ok": True}
