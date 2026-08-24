from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from app.models.entities import ExternalRecipient, FileObject, InteractionTransaction, MeetingLog, User


def build_relationship_graph(db: DBSession, *, limit: int = 200) -> dict:
    txs = (
        db.query(InteractionTransaction)
        .filter(InteractionTransaction.is_deleted.is_(False))
        .order_by(InteractionTransaction.occurred_at.desc())
        .limit(limit)
        .all()
    )
    meetings = (
        db.query(MeetingLog)
        .filter(MeetingLog.is_deleted.is_(False))
        .order_by(MeetingLog.occurred_at.desc())
        .limit(limit)
        .all()
    )
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add_node(nid: str, ntype: str, label: str) -> None:
        if nid not in nodes:
            nodes[nid] = {"id": nid, "type": ntype, "label": label}

    for tx in txs:
        rec_id = f"recipient:{tx.recipient_id or tx.recipient_name}"
        add_node(rec_id, "recipient", tx.recipient_name)
        actor = db.query(User).filter(User.id == tx.logged_by_user_id).one_or_none()
        actor_id = f"user:{tx.logged_by_user_id}"
        add_node(actor_id, "user", actor.full_name if actor else tx.logged_by_user_id)
        occurred = tx.occurred_at.isoformat() if tx.occurred_at else ""
        edges.append({"from": actor_id, "to": rec_id, "kind": tx.kind, "purpose": tx.purpose, "at": occurred})
        if tx.file_id:
            file = db.query(FileObject).filter(FileObject.id == tx.file_id).one_or_none()
            file_node = f"file:{tx.file_id}"
            add_node(file_node, "file", file.title if file else tx.file_id)
            edges.append({"from": file_node, "to": rec_id, "kind": "file_delivery", "purpose": tx.purpose, "at": occurred})

    for meeting in meetings:
        mid = f"meeting:{meeting.id}"
        add_node(mid, "meeting", meeting.title)
        occurred = meeting.occurred_at.isoformat() if meeting.occurred_at else ""
        for name in meeting.attendees or []:
            nid = f"attendee:{name}"
            add_node(nid, "attendee", name)
            edges.append({"from": mid, "to": nid, "kind": meeting.meeting_kind, "purpose": "meeting", "at": occurred})

    recipients = db.query(ExternalRecipient).filter(ExternalRecipient.is_active.is_(True)).limit(limit).all()
    for rec in recipients:
        add_node(f"recipient:{rec.id}", "recipient", rec.full_name)

    return {"offline_only": True, "localhost_only": True, "nodes": list(nodes.values()), "edges": edges}
