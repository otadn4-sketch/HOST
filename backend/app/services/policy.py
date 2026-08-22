from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from app.models.entities import SecurityPolicy
from app.security.constants import DEFAULT_ALLOWED_EXTENSIONS


def get_or_create_policy(db: DBSession) -> SecurityPolicy:
    policy = db.query(SecurityPolicy).filter(SecurityPolicy.id == 1).one_or_none()
    if policy is None:
        policy = SecurityPolicy(
            id=1,
            allowed_extensions=list(DEFAULT_ALLOWED_EXTENSIONS),
            max_file_size_bytes=52_428_800,
            clamav_enabled=True,
            quarantine_dangerous_files=True,
            session_timeout_minutes=30,
            max_failed_login_attempts=5,
            lockout_duration_minutes=15,
            password_min_length=12,
            require_special_chars=True,
        )
        db.add(policy)
        db.flush()
    return policy
