from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session as DBSession

from app.models.entities import AiSettings, SecurityPolicy, SmsSettings
from app.security.constants import DEFAULT_ALLOWED_EXTENSIONS
from app.services.ai_prompts import DEFAULT_CHAT_PROMPT, DEFAULT_SUMMARIZE_PROMPT


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


def get_or_create_ai_settings(db: DBSession) -> AiSettings:
    row = db.query(AiSettings).filter(AiSettings.id == 1).one_or_none()
    if row is None:
        row = AiSettings(
            id=1,
            chat_prompt=DEFAULT_CHAT_PROMPT,
            summarize_prompt=DEFAULT_SUMMARIZE_PROMPT,
        )
        db.add(row)
        db.flush()
    else:
        if not (row.chat_prompt or "").strip():
            row.chat_prompt = DEFAULT_CHAT_PROMPT
        if not (row.summarize_prompt or "").strip():
            row.summarize_prompt = DEFAULT_SUMMARIZE_PROMPT
    return row


def get_or_create_sms_settings(db: DBSession, settings=None) -> SmsSettings:
    from app.config import get_settings
    settings = settings or get_settings()
    row = db.query(SmsSettings).filter(SmsSettings.id == 1).one_or_none()
    if row is None:
        row = SmsSettings(
            id=1,
            enabled=bool(settings.sms_enabled),
            base_url=settings.sms_base_url or "",
            api_key=settings.sms_api_key or "",
            sender=settings.sms_sender or "",
            http_method=(settings.sms_http_method or "POST").upper(),
            content_type=(settings.sms_content_type or "json").lower(),
            url_template=settings.sms_url_template or "",
            body_template=settings.sms_body_template or "",
            auth_header_name=settings.sms_auth_header_name or "",
            extra_headers={},
        )
        db.add(row)
        db.flush()
    return row


def ensure_runtime_schema(db: DBSession) -> None:
    """Add columns/tables introduced after 1.0.0 on existing databases."""
    bind = db.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())
    if "users" in tables:
        cols = {c["name"] for c in insp.get_columns("users")}
        if "org_role_id" not in cols:
            db.execute(text("ALTER TABLE users ADD COLUMN org_role_id VARCHAR(36)"))
            db.flush()
    if "files" in tables:
        file_cols = {c["name"] for c in insp.get_columns("files")}
        statements = []
        if "authors" not in file_cols:
            statements.append("ALTER TABLE files ADD COLUMN authors JSON")
        if "excel_logged" not in file_cols:
            statements.append("ALTER TABLE files ADD COLUMN excel_logged JSON")
        if "faran_remote_id" not in file_cols:
            statements.append("ALTER TABLE files ADD COLUMN faran_remote_id VARCHAR(128)")
        for stmt in statements:
            db.execute(text(stmt))
        if statements:
            db.flush()
    if "document_scrub_jobs" in tables:
        scrub_cols = {c["name"] for c in insp.get_columns("document_scrub_jobs")}
        if "result_file_id" not in scrub_cols:
            db.execute(text("ALTER TABLE document_scrub_jobs ADD COLUMN result_file_id VARCHAR(36)"))
        if "redacted_count" not in scrub_cols:
            db.execute(text("ALTER TABLE document_scrub_jobs ADD COLUMN redacted_count INTEGER DEFAULT 0"))
        db.flush()
