from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db, require_system_admin
from app.config import get_settings
from app.models.entities import User, utcnow
from app.schemas import AiPromptsPatchIn, PolicyPatchIn
from app.security.constants import DANGEROUS_EXTENSIONS
from app.security.rbac import is_admin
from app.services.audit import write_audit
from app.services.policy import get_or_create_ai_settings, get_or_create_policy

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _full_policy(policy) -> dict:
    return {
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


def _public_policy(policy) -> dict:
    return {
        "allowed_extensions": policy.allowed_extensions,
        "max_file_size_bytes": policy.max_file_size_bytes,
        "clamav_scan_enabled": False,
        "quarantine_dangerous_files": True,
        "session_timeout_minutes": policy.session_timeout_minutes,
        "max_failed_login_attempts": None,
        "lockout_duration_minutes": None,
        "password_min_length": policy.password_min_length,
        "require_special_chars": policy.require_special_chars,
        "vault_storage_path": "",
        "allow_direct_path_access": False,
        "enforce_https": True,
    }


@router.get("/policy")
def get_policy(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    policy = get_or_create_policy(db)
    body = _full_policy(policy) if is_admin(user) else _public_policy(policy)
    return {"policy": body}


@router.get("/infrastructure")
def infrastructure(user: User = Depends(require_system_admin)):
    settings = get_settings()
    return {
        "infrastructure": {
            "host": "Linux / Docker (on-premise)",
            "vault": "volume محلی ایزوله",
            "scanner": "ClamAV محلی" if not settings.clamav_disabled else "پویش غیرفعال (محیط آزمون)",
            "https": True,
        }
    }


@router.get("/ai-prompts")
def get_ai_prompts(db: DBSession = Depends(get_db), user: User = Depends(require_system_admin)):
    row = get_or_create_ai_settings(db)
    return {"prompts": {"chat_prompt": row.chat_prompt, "summarize_prompt": row.summarize_prompt}}


@router.put("/ai-prompts")
def update_ai_prompts(
    payload: AiPromptsPatchIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_system_admin),
):
    row = get_or_create_ai_settings(db)
    if payload.chat_prompt is not None:
        text = payload.chat_prompt.strip()
        if len(text) < 20:
            raise HTTPException(status_code=400, detail="پرامپت گفت‌وگو خیلی کوتاه است.")
        row.chat_prompt = text
    if payload.summarize_prompt is not None:
        text = payload.summarize_prompt.strip()
        if len(text) < 20:
            raise HTTPException(status_code=400, detail="پرامپت خلاصه‌سازی خیلی کوتاه است.")
        row.summarize_prompt = text
    row.updated_at = utcnow()
    write_audit(
        db,
        user=user,
        action="security_policy_change",
        target_resource="پرامپت هوش مصنوعی",
        details="به‌روزرسانی پرامپت گفت‌وگو/خلاصه",
        severity="warning",
        request=request,
    )
    return {"prompts": {"chat_prompt": row.chat_prompt, "summarize_prompt": row.summarize_prompt}}


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
    return {"policy": _full_policy(policy)}
