from datetime import datetime, timezone

from tests.conftest import auth_header, login, seed_user


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_ac12_manual_transaction_logging_and_search(client):
    seed_user("admin", "system_admin")
    seed_user("alice", "user", email="alice@eytan.local")
    seed_user("viewer1", "viewer", email="viewer1@eytan.local")

    login(client, "alice")
    headers = auth_header(client)
    upload = client.post(
        "/api/files",
        headers=headers,
        files={"file": ("note.txt", "گزارش آزمون\n".encode("utf-8"), "text/plain")},
        data={"title": "گزارش سیاستی", "topic": "آزمون", "classification": "internal"},
    )
    assert upload.status_code == 200, upload.text
    file_id = upload.json()["file"]["id"]

    blocked = client.post(
        "/api/transactions",
        headers=headers,
        json={
            "file_id": file_id,
            "recipient_name": "نهاد الف",
            "recipient_organization": "مجلس",
            "occurred_at": _iso(),
            "purpose": "ارسال خودکار ممنوع",
            "channel": "telegram",
            "create_recipient": True,
        },
    )
    assert blocked.status_code == 400

    created = client.post(
        "/api/transactions",
        headers=headers,
        json={
            "file_id": file_id,
            "recipient_name": "کمیسیون تخصصی",
            "recipient_organization": "مجلس شورای اسلامی",
            "request_origin": "درخواست کتبی",
            "occurred_at": _iso(),
            "purpose": "تحویل نسخه چاپی گزارش",
            "channel": "handoff",
            "notes": "تحویل حضوری در جلسه",
            "create_recipient": True,
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()["transaction"]
    assert body["automated"] is False
    assert body["recipient_name"] == "کمیسیون تخصصی"
    assert body["file_id"] == file_id
    tx_id = body["id"]

    listed = client.get("/api/transactions", headers=headers, params={"q": "کمیسیون"})
    assert listed.status_code == 200
    assert listed.json()["automated_delivery_enabled"] is False
    assert any(item["id"] == tx_id for item in listed.json()["transactions"])

    filtered = client.get("/api/transactions", headers=headers, params={"purpose": "چاپی"})
    assert any(item["id"] == tx_id for item in filtered.json()["transactions"])

    recipients = client.get("/api/recipients", headers=headers)
    assert recipients.status_code == 200
    assert any(item["full_name"] == "کمیسیون تخصصی" for item in recipients.json()["recipients"])

    client.post("/api/auth/logout", headers=headers)
    login(client, "viewer1")
    viewer_headers = auth_header(client)
    denied = client.post(
        "/api/transactions",
        headers=viewer_headers,
        json={
            "recipient_name": "نهاد ب",
            "occurred_at": _iso(),
            "purpose": "نباید ثبت شود",
            "channel": "handoff",
        },
    )
    assert denied.status_code == 403


def test_ac12_phases_faran_stub_and_graph_isolation(client):
    seed_user("admin", "system_admin")
    login(client, "admin")
    headers = auth_header(client)

    phases = client.get("/api/phases", headers=headers)
    assert phases.status_code == 200
    payload = phases.json()
    assert payload["automated_delivery_enabled"] is False
    assert payload["automated_delivery_deprecated"] is True
    flags = {item["flag"]: item["enabled"] for item in payload["phases"]}
    assert flags["phase_1_archive_enabled"] is True
    assert flags["phase_4_sharing_enabled"] is False
    assert flags["phase_5_security_graph_enabled"] is False

    faran = client.get("/api/faran/status", headers=headers)
    assert faran.status_code == 200
    assert faran.json()["faran"]["mode"] == "stub"

    sync = client.post("/api/faran/sync", headers=headers)
    assert sync.status_code == 200
    assert sync.json()["sync"]["status"] == "stub"

    shares = client.post("/api/shares", headers=headers, json={"file_id": "x"})
    assert shares.status_code in {403, 501}

    graph = client.get("/api/graph/relationships", headers=headers)
    assert graph.status_code == 403

    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "نشست هماهنگی",
            "meeting_kind": "physical_meeting",
            "occurred_at": _iso(),
            "location": "تهران",
            "attendees": ["نماینده الف"],
            "agenda": "بررسی گزارش",
            "outcome": "تحویل نسخه چاپی",
        },
    )
    assert meeting.status_code == 200, meeting.text
    listed = client.get("/api/meetings", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["meetings"]
