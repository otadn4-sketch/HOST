from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db
from app.models.entities import AuditLog, User
from app.security.rbac import can_read_audit, is_admin
from app.services.audit import write_audit

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
def list_logs(
    request: Request,
    q: str = "",
    action: str | None = None,
    severity: str | None = None,
    log_id: str | None = None,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_read_audit(user):
        write_audit(
            db,
            user=user,
            action="suspicious_activity",
            target_resource="audit-logs",
            details="تلاش غیرمجاز برای مشاهده لاگ",
            severity="warning",
            request=request,
        )
        raise HTTPException(status_code=403, detail="دسترسی به لاگ ندارید.")
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if not is_admin(user):
        query = query.filter(AuditLog.user_id == user.id)
    admin = is_admin(user)
    if log_id:
        row = query.filter(AuditLog.id == log_id).one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="رخداد یافت نشد.")
        return {"logs": [_ser(row, admin)]}
    rows = query.limit(500).all()
    result = []
    for row in rows:
        if action and action != "all" and row.action != action:
            continue
        if severity and severity != "all" and row.severity != severity:
            continue
        if q.strip():
            blob = " ".join([row.username, row.action_title, row.target_resource, row.details, row.ip_address if admin else ""]).lower()
            if q.strip().lower() not in blob:
                continue
        result.append(_ser(row, admin))
    return {"logs": result}


@router.get("/export")
def export_logs(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    if not can_read_audit(user):
        raise HTTPException(status_code=403, detail="دسترسی به لاگ ندارید.")
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(2000)
    if not is_admin(user):
        query = query.filter(AuditLog.user_id == user.id)
    rows = query.all()
    admin = is_admin(user)
    lines = ["id,timestamp,username,role,action,target,ip,severity,details"] if admin else [
        "id,timestamp,username,role,action,target,severity,details"
    ]
    for r in rows:
        details = (r.details or "").replace('"', "'")
        if admin:
            lines.append(
                f'{r.id},{r.timestamp.isoformat()},{r.username},{r.user_role},{r.action},"{r.target_resource}",{r.ip_address},{r.severity},"{details}"'
            )
        else:
            lines.append(
                f'{r.id},{r.timestamp.isoformat()},{r.username},{r.user_role},{r.action},"{r.target_resource}",{r.severity},"{details}"'
            )
    data = ("\ufeff" + "\n".join(lines)).encode("utf-8")
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="audit-logs.csv"'},
    )


def _ser(row: AuditLog, admin: bool) -> dict:
    return {
        "id": row.id,
        "timestamp": row.timestamp,
        "user_id": row.user_id,
        "username": row.username,
        "user_role": row.user_role,
        "action": row.action,
        "action_title": row.action_title,
        "target_resource": row.target_resource,
        "details": row.details,
        "ip_address": row.ip_address if admin else "",
        "user_agent": row.user_agent if admin else "",
        "severity": row.severity,
    }
