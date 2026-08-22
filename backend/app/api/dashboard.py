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

    visit_q = db.query(AuditLog).filter(AuditLog.action == "file_preview")
    if since:
        visit_q = visit_q.filter(AuditLog.timestamp >= since)
    visit_logs = visit_q.all()

    active_users = 0
    for u in users:
        last = aware(u.last_login_at)
        if last and (since is None or last >= since):
            active_users += 1

    view_count = len(visit_logs)
    unique_people = len({l.user_id or l.username for l in visit_logs})
    download_count = sum(1 for l in logs if l.action == "file_download")
    file_topics: dict[str, int] = {}
    for f in files:
        if f.topic:
            file_topics[f.topic] = file_topics.get(f.topic, 0) + f.view_count + f.download_count

    pair_counts: dict[tuple[str, str], int] = {}
    for l in visit_logs:
        pair_counts[(l.target_resource or "—", l.username or "—")] = (
            pair_counts.get((l.target_resource or "—", l.username or "—"), 0) + 1
        )
    file_totals: dict[str, int] = {}
    user_totals: dict[str, int] = {}
    for (fname, uname), c in pair_counts.items():
        file_totals[fname] = file_totals.get(fname, 0) + c
        user_totals[uname] = user_totals.get(uname, 0) + c
    top_files = sorted(file_totals, key=file_totals.get, reverse=True)[:8]
    top_users = sorted(user_totals, key=user_totals.get, reverse=True)[:8]
    file_viewer_chart = []
    for fname in top_files:
        row: dict = {"file": fname[:40]}
        for uname in top_users:
            row[uname] = pair_counts.get((fname, uname), 0)
        file_viewer_chart.append(row)
    file_viewers = [
        {"file": f, "user": u, "visits": c}
        for (f, u), c in sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:40]
    ]

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
            "file_preview",
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
            "views_total": view_count,
            "views_unique": unique_people,
            "downloads": download_count,
            "files_total": len([f for f in files if f.is_current_version]),
            "quarantined": len([f for f in files if f.scan_status == "quarantined"]),
        },
        "top_topics": sorted(
            [{"topic": k, "count": v} for k, v in file_topics.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10],
        "file_viewer_chart": file_viewer_chart,
        "file_viewer_users": top_users,
        "file_viewers": file_viewers,
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
