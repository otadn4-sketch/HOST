from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from app.models.entities import Session, User, utcnow


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def new_csrf_secret() -> str:
    return secrets.token_hex(32)


def create_session(
    db,
    user: User,
    *,
    timeout_minutes: int,
    ip: str,
    user_agent: str,
) -> tuple[Session, str]:
    token = new_session_token()
    now = utcnow()
    session = Session(
        user_id=user.id,
        token_hash=hash_token(token),
        csrf_secret=new_csrf_secret(),
        created_at=now,
        expires_at=now + timedelta(minutes=timeout_minutes),
        last_seen_at=now,
        ip_address=ip[:64],
        user_agent=(user_agent or "")[:512],
    )
    db.add(session)
    db.flush()
    return session, token


def get_valid_session(db, token: str) -> Session | None:
    if not token:
        return None
    row = db.query(Session).filter(Session.token_hash == hash_token(token)).one_or_none()
    if row is None:
        return None
    now = utcnow()
    if row.revoked_at is not None:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        return None
    return row


def touch_session(session: Session, timeout_minutes: int) -> None:
    session.last_seen_at = utcnow()
    session.expires_at = utcnow() + timedelta(minutes=timeout_minutes)


def revoke_session(session: Session) -> None:
    session.revoked_at = utcnow()


def revoke_all_user_sessions(db, user_id: str) -> None:
    now = utcnow()
    db.query(Session).filter(Session.user_id == user_id, Session.revoked_at.is_(None)).update(
        {Session.revoked_at: now}, synchronize_session=False
    )


def csrf_tokens_match(expected: str, provided: str) -> bool:
    if not expected or not provided:
        return False
    return hmac.compare_digest(expected, provided)
