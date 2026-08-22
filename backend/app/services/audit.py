from __future__ import annotations

from fastapi import Request

from app.models.entities import AuditLog, User
from app.security.constants import ACTION_TITLES, ROLE_TITLES


def client_ip(request: Request | None) -> str:
    if request is None:
        return ""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return (request.client.host or "")[:64]
    return ""


def user_agent(request: Request | None) -> str:
    if request is None:
        return ""
    return (request.headers.get("user-agent") or "")[:512]


def write_audit(
    db,
    *,
    user: User | None,
    action: str,
    target_resource: str = "",
    details: str = "",
    severity: str = "info",
    request: Request | None = None,
    target_type: str = "",
    target_id: str = "",
    username_override: str = "",
) -> AuditLog:
    log = AuditLog(
        user_id=user.id if user else None,
        username=(user.username if user else username_override)[:80],
        user_role=user.role if user else "",
        action=action,
        action_title=ACTION_TITLES.get(action, action),
        target_type=target_type,
        target_id=target_id,
        target_resource=target_resource[:400],
        details=details[:4000],
        ip_address=client_ip(request),
        user_agent=user_agent(request),
        severity=severity,
    )
    db.add(log)
    db.flush()
    return log


def role_title(role: str) -> str:
    return ROLE_TITLES.get(role, role)
