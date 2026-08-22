from tests.conftest import STRONG, auth_header, login, seed_user


def test_ac02_rbac_and_idor(client):
    seed_user("admin", "system_admin")
    seed_user("alice", "user", email="alice@eytan.local")
    seed_user("bob", "user", email="bob@eytan.local")
    seed_user("view", "viewer", email="view@eytan.local")

    login(client, "alice")
    h = auth_header(client)
    up = client.post(
        "/api/files",
        headers=h,
        files={"file": ("note.txt", b"alice secret report\n", "text/plain")},
        data={"title": "سند آلیس", "topic": "آزمون", "classification": "confidential"},
    )
    assert up.status_code == 200, up.text
    file_id = up.json()["file"]["id"]
    assert up.json()["file"]["scan_status"] in {"clean", "quarantined"}

    client.post("/api/auth/logout", headers=h)
    login(client, "bob")
    hb = auth_header(client)
    hidden = client.get(f"/api/files/{file_id}", headers=hb)
    assert hidden.status_code == 404
    dl = client.get(f"/api/files/{file_id}/download", headers=hb)
    assert dl.status_code == 404
    # user enumeration / IDOR on users
    users = client.get("/api/users", headers=hb).json()["users"]
    assert all(u["username"] in {"bob"} for u in users)

    client.post("/api/auth/logout", headers=hb)
    login(client, "view")
    hv = auth_header(client)
    upload = client.post(
        "/api/files",
        headers=hv,
        files={"file": ("x.txt", b"nope\n", "text/plain")},
        data={"title": "نباید", "topic": "x"},
    )
    assert upload.status_code == 403
    dash = client.get("/api/dashboard", headers=hv)
    assert dash.status_code == 403
