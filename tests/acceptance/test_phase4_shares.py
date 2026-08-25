from datetime import datetime, timedelta, timezone

from tests.conftest import auth_header, login, seed_user


def _enable_phase4():
    from app.config import get_settings

    settings = get_settings()
    settings.phase_4_sharing_enabled = True
    return settings


def _upload(client, headers, name="note.txt", body=b"shared-bytes\n"):
    up = client.post(
        "/api/files",
        headers=headers,
        files={"file": (name, body, "text/plain")},
        data={"title": "سند اشتراک", "topic": "آزمون", "classification": "confidential"},
    )
    assert up.status_code == 200, up.text
    return up.json()["file"]["id"]


def test_phase4_disabled_rejects_share_api(client):
    seed_user("admin", "system_admin")
    login(client, "admin")
    h = auth_header(client)
    listed = client.get("/api/shares", headers=h)
    assert listed.status_code == 403
    created = client.post("/api/shares", headers=h, json={"file_id": "x", "grantee_user_id": "y"})
    assert created.status_code == 403


def test_phase4_share_create_use_revoke_expiry_idor(client):
    settings = _enable_phase4()
    admin_id, _ = seed_user("admin", "system_admin")
    alice_id, _ = seed_user("alice", "user", email="alice@eytan.local")
    bob_id, _ = seed_user("bob", "user", email="bob@eytan.local")
    seed_user("view", "viewer", email="view@eytan.local")

    login(client, "alice")
    ha = auth_header(client)
    file_id = _upload(client, ha)

    public = client.post(
        "/api/shares",
        headers=ha,
        json={"file_id": file_id, "grantee_user_id": bob_id, "audience": "public", "can_download": True},
    )
    assert public.status_code == 400

    created = client.post(
        "/api/shares",
        headers=ha,
        json={
            "file_id": file_id,
            "grantee_user_id": bob_id,
            "can_download": True,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            "purpose": "بازبینی داخلی",
        },
    )
    assert created.status_code == 200, created.text
    share_id = created.json()["share"]["id"]
    assert created.json()["share"]["public"] is False

    client.post("/api/auth/logout", headers=ha)
    login(client, "view")
    hv = auth_header(client)
    viewer_create = client.post(
        "/api/shares",
        headers=hv,
        json={"file_id": file_id, "grantee_user_id": bob_id, "can_download": True},
    )
    assert viewer_create.status_code == 403
    viewer_dl = client.get(f"/api/shares/{share_id}/download", headers=hv)
    assert viewer_dl.status_code in {403, 404}

    client.post("/api/auth/logout", headers=hv)
    login(client, "bob")
    hb = auth_header(client)
    hidden = client.get(f"/api/files/{file_id}/download", headers=hb)
    assert hidden.status_code == 404
    shared = client.get(f"/api/shares/{share_id}/download", headers=hb)
    assert shared.status_code == 200, shared.text
    assert shared.content == b"shared-bytes\n"

    client.post("/api/auth/logout", headers=hb)
    login(client, "alice")
    ha = auth_header(client)
    past = client.post(
        "/api/shares",
        headers=ha,
        json={
            "file_id": file_id,
            "grantee_user_id": bob_id,
            "can_download": True,
            "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        },
    )
    assert past.status_code == 400

    from app.api.deps import _SessionLocal
    from app.models.entities import ShareLink

    db = _SessionLocal()
    try:
        row = db.query(ShareLink).filter(ShareLink.id == share_id).one()
        row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    client.post("/api/auth/logout", headers=ha)
    login(client, "bob")
    hb = auth_header(client)
    expired = client.get(f"/api/shares/{share_id}/download", headers=hb)
    assert expired.status_code == 403

    db = _SessionLocal()
    try:
        row = db.query(ShareLink).filter(ShareLink.id == share_id).one()
        row.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
    finally:
        db.close()

    client.post("/api/auth/logout", headers=hb)
    login(client, "alice")
    ha = auth_header(client)
    revoked = client.post(f"/api/shares/{share_id}/revoke", headers=ha)
    assert revoked.status_code == 200
    client.post("/api/auth/logout", headers=ha)
    login(client, "bob")
    hb = auth_header(client)
    after = client.get(f"/api/shares/{share_id}/download", headers=hb)
    assert after.status_code == 403

    other = client.get("/api/shares/not-a-real-id", headers=hb)
    assert other.status_code == 404
    settings.phase_4_sharing_enabled = False
