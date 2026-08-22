from __future__ import annotations

from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.config import Settings, get_settings
from app.db import make_engine, make_session_factory
from app.models.entities import User
from app.security.rbac import can_see_dashboard, is_admin
from app.security.sessions import csrf_tokens_match, get_valid_session, touch_session
from app.services.policy import get_or_create_policy

_engine = None
_SessionLocal = None


def get_engine(settings: Settings | None = None):
    global _engine, _SessionLocal
    settings = settings or get_settings()
    if _engine is None:
        _engine = make_engine(settings.database_url)
        _SessionLocal = make_session_factory(_engine)
    return _engine


def get_db():
    get_engine()
    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except HTTPException:
        db.commit()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_current_user(
    request: Request,
    db: DBSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    session_cookie: str | None = Cookie(default=None, alias=None),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    session = get_valid_session(db, token or "")
    if session is None:
        raise HTTPException(status_code=401, detail="نشست نامعتبر است. دوباره وارد شوید.")
    user = db.query(User).filter(User.id == session.user_id).one_or_none()
    if user is None or user.status != "active":
        raise HTTPException(status_code=401, detail="حساب کاربری غیرفعال است.")
    policy = get_or_create_policy(db)
    if request.method not in SAFE_METHODS:
        provided = csrf_header or request.headers.get("x-csrf-token")
        if not csrf_tokens_match(session.csrf_secret, provided or ""):
            raise HTTPException(status_code=403, detail="توکن CSRF نامعتبر است.")
    touch_session(session, policy.session_timeout_minutes)
    request.state.session = session
    request.state.user = user
    return user


def require_system_admin(user: User = Depends(get_current_user)) -> User:
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="این عملیات فقط برای مدیر سامانه مجاز است.")
    return user


def require_dashboard(user: User = Depends(get_current_user)) -> User:
    if not can_see_dashboard(user):
        raise HTTPException(status_code=403, detail="داشبورد فقط برای مدیر سامانه در دسترس است.")
    return user
