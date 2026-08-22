from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session as DBSession

from app.models.entities import AiSettings, SecurityPolicy
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
