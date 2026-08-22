from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db, require_system_admin
from app.models.entities import User
from app.schemas import PolicyPatchIn
from app.security.constants import DANGEROUS_EXTENSIONS
from app.services.audit import write_audit
from app.services.policy import get_or_create_policy

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/policy")
def get_policy(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    policy = get_or_create_policy(db)
    return {
        "policy": {
            "allowed_extensions": policy.allowed_extensions,
            "max_file_size_bytes": policy.max_file_size_bytes,
            "clamav_scan_enabled": policy.clamav_enabled,
            "quarantine_dangerous_files": policy.quarantine_dangerous_files,
            "session_timeout_minutes": policy.session_timeout_minutes,
            "max_failed_login_attempts": policy.max_failed_login_attempts,
            "lockout_duration_minutes": policy.lockout_duration_minutes,
            "password_min_length": policy.password_min_length,
            "require_special_chars": policy.require_special_chars,
            "vault_storage_path": "(server-side, not exposed)",
            "allow_direct_path_access": False,
            "enforce_https": True,
        }
    }


@router.put("/policy")
def update_policy(
    payload: PolicyPatchIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_system_admin),
):
    policy = get_or_create_policy(db)
    if payload.allowed_extensions is not None:
        cleaned = []
        for ext in payload.allowed_extensions:
            e = ext.lower().lstrip(".")
            if e in DANGEROUS_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"فرمت اجرایی {e} قابل فعال‌سازی نیست.")
            cleaned.append(e)
        policy.allowed_extensions = cleaned
    if payload.max_file_size_bytes is not None:
        if payload.max_file_size_bytes < 1024 or payload.max_file_size_bytes > 1024 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="سقف حجم نامعتبر است.")
        policy.max_file_size_bytes = payload.max_file_size_bytes
    if payload.clamav_scan_enabled is not None:
        policy.clamav_enabled = payload.clamav_scan_enabled
    if payload.quarantine_dangerous_files is not None:
        policy.quarantine_dangerous_files = payload.quarantine_dangerous_files
    if payload.session_timeout_minutes is not None:
        policy.session_timeout_minutes = max(5, min(payload.session_timeout_minutes, 12 * 60))
    if payload.max_failed_login_attempts is not None:
        policy.max_failed_login_attempts = max(3, min(payload.max_failed_login_attempts, 20))
    if payload.lockout_duration_minutes is not None:
        policy.lockout_duration_minutes = max(5, min(payload.lockout_duration_minutes, 24 * 60))
    if payload.password_min_length is not None:
        policy.password_min_length = max(8, min(payload.password_min_length, 64))
    if payload.require_special_chars is not None:
        policy.require_special_chars = payload.require_special_chars
    write_audit(
        db,
        user=user,
        action="security_policy_change",
        target_resource="سیاست امنیتی",
        details="به‌روزرسانی سیاست فرمت/حجم/نشست",
        severity="warning",
        request=request,
    )
    return get_policy(db, user)
