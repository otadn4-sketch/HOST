from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_db, require_dashboard
from app.models.entities import AuditLog, FileObject, User, aware

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _since(range_key: str) -> datetime | None:
    now = datetime.now(timezone.utc)
    mapping = {
        "today": timedelta(days=1),
        "3days": timedelta(days=3),
        "week": timedelta(days=7),
        "month": timedelta(days=30),
        "all": None,
    }
    delta = mapping.get(range_key, timedelta(days=7))
    return None if delta is None else now - delta


@router.get("")
def dashboard(
    range: str = Query("week"),
    db: DBSession = Depends(get_db),
    user: User = Depends(require_dashboard),
):
    since = _since(range)
    users = db.query(User).all()
    files = db.query(FileObject).filter(FileObject.is_deleted.is_(False)).all()
    logs_q = db.query(AuditLog)
    if since:
        logs_q = logs_q.filter(AuditLog.timestamp >= since)
    logs = logs_q.order_by(AuditLog.timestamp.desc()).limit(1000).all()

    active_users = 0
    for u in users:
        last = aware(u.last_login_at)
        if last and (since is None or last >= since):
            active_users += 1

    view_count = sum(1 for l in logs if l.action == "file_view")
    download_count = sum(1 for l in logs if l.action == "file_download")
    topics: dict[str, int] = {}
    for l in logs:
        if l.action in {"file_view", "file_download"}:
            topics[l.target_resource] = topics.get(l.target_resource, 0) + 1
    file_topics: dict[str, int] = {}
    for f in files:
        if f.topic:
            file_topics[f.topic] = file_topics.get(f.topic, 0) + f.view_count + f.download_count

    events = [
        {
            "user": l.username,
            "file": l.target_resource,
            "topic": next((f.topic for f in files if f.id == l.target_id), ""),
            "action": l.action,
            "action_title": l.action_title,
            "severity": l.severity,
            "timestamp": l.timestamp,
        }
        for l in logs
        if l.action
        in {
            "file_view",
            "file_download",
            "file_upload",
            "login_success",
            "login_failed",
            "file_quarantined",
            "permission_change",
            "system_update",
            "ai_chat",
            "ai_summarize",
        }
    ][:200]

    action_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    user_counts: dict[str, int] = {}
    for e in events:
        action_counts[e["action_title"]] = action_counts.get(e["action_title"], 0) + 1
        severity_counts[e["severity"]] = severity_counts.get(e["severity"], 0) + 1
        user_counts[e["user"]] = user_counts.get(e["user"], 0) + 1

    return {
        "kpis": {
            "users_total": len(users),
            "users_active": active_users,
            "views": view_count,
            "downloads": download_count,
            "files_total": len([f for f in files if f.is_current_version]),
            "quarantined": len([f for f in files if f.scan_status == "quarantined"]),
        },
        "top_topics": sorted(
            [{"topic": k, "count": v} for k, v in file_topics.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10],
        "events": events,
        "event_by_action": sorted(
            [{"name": k, "count": v} for k, v in action_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        ),
        "event_by_severity": [{"name": k, "count": v} for k, v in severity_counts.items()],
        "event_by_user": sorted(
            [{"name": k, "count": v} for k, v in user_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:12],
    }
