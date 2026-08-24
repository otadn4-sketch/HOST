from tests.conftest import STRONG, auth_header, login, seed_user


def test_security_fields_hidden_from_non_admin(client):
    seed_user("admin", "system_admin")
    seed_user("alice", "user", email="alice@eytan.local")
    login(client, "alice")
    h = auth_header(client)
    up = client.post(
        "/api/files",
        headers=h,
        files={"file": ("note.txt", b"alice report text\n", "text/plain")},
        data={"title": "سند آلیس", "topic": "آزمون", "classification": "internal"},
    )
    assert up.status_code == 200, up.text
    body = up.json()["file"]
    assert body["checksum_sha256"] == ""
    assert body["stored_vault_name"] == ""
    assert body["quarantine_reason"] is None

    client.post("/api/auth/logout", headers=h)
    login(client, "admin")
    ha = auth_header(client)
    detail = client.get(f"/api/files/{body['id']}", headers=ha)
    assert detail.status_code == 200
    admin_file = detail.json()["file"]
    assert len(admin_file["checksum_sha256"]) == 64
    assert admin_file["stored_vault_name"]


def test_org_unit_and_role_crud(client):
    seed_user("admin", "system_admin")
    login(client, "admin")
    h = auth_header(client)
    created = client.post(
        "/api/groups",
        headers=h,
        json={"name": "واحد آزمون", "code": "TSTU", "max_file_size_mb": 12, "allowed_file_extensions": ["txt"]},
    )
    assert created.status_code == 200, created.text
    gid = created.json()["group"]["id"]
    patched = client.patch(f"/api/groups/{gid}", headers=h, json={"name": "واحد آزمون ویرایش", "code": "TST2"})
    assert patched.status_code == 200
    assert patched.json()["group"]["name"] == "واحد آزمون ویرایش"
    deleted = client.delete(f"/api/groups/{gid}", headers=h)
    assert deleted.status_code == 200

    roles = client.get("/api/roles", headers=h)
    assert roles.status_code == 200
    assert len(roles.json()["roles"]) >= 4
    custom = client.post(
        "/api/roles",
        headers=h,
        json={"name": "کارشناس مالی", "code": "FIN-EXP", "description": "کاربر واحد مالی", "permission_level": "user"},
    )
    assert custom.status_code == 200, custom.text
    rid = custom.json()["role"]["id"]
    renamed = client.patch(f"/api/roles/{rid}", headers=h, json={"name": "کارشناس بودجه"})
    assert renamed.json()["role"]["name"] == "کارشناس بودجه"
    assert client.delete(f"/api/roles/{rid}", headers=h).status_code == 200


def test_ai_chat_and_summarize_and_prompts(client):
    seed_user("alice", "user")
    login(client, "alice")
    h = auth_header(client)
    up = client.post(
        "/api/files",
        headers=h,
        files={"file": ("policy.txt", b"password policy argon2\n", "text/plain")},
        data={"title": "سیاست گذرواژه", "topic": "امنیت", "classification": "internal", "description": "الزام Argon2"},
    )
    assert up.status_code == 200
    file_id = up.json()["file"]["id"]
    chat = client.post("/api/ai/chat", headers=h, json={"message": "خلاصه منابع چیست؟", "file_ids": [file_id]})
    assert chat.status_code == 410
    summary = client.post("/api/ai/summarize", headers=h, json={"file_id": file_id, "mode": "executive"})
    assert summary.status_code == 200
    assert "خلاصه" in summary.json()["summary"] or "چکیده" in summary.json()["summary"]
    prompts = client.get("/api/settings/ai-prompts", headers=h)
    assert prompts.status_code == 403
