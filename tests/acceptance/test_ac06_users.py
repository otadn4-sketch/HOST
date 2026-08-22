from tests.conftest import STRONG, auth_header, login, seed_user


def test_ac06_user_and_group_admin(client):
    seed_user("admin", "system_admin")
    login(client, "admin")
    h = auth_header(client)
    groups = client.get("/api/groups", headers=h).json()["groups"]
    gid = groups[0]["id"]
    created = client.post(
        "/api/users",
        headers=h,
        json={
            "username": "newuser",
            "full_name": "کاربر جدید",
            "email": "newuser@eytan.local",
            "role": "user",
            "group_id": gid,
            "password": STRONG,
        },
    )
    assert created.status_code == 200, created.text
    uid = created.json()["user"]["id"]
    patched = client.patch(f"/api/users/{uid}", headers=h, json={"status": "suspended"})
    assert patched.status_code == 200
    assert patched.json()["user"]["status"] == "suspended"
    g = client.post(
        "/api/groups",
        headers=h,
        json={"name": "گروه آزمون", "code": "TEST1", "max_file_size_mb": 10, "allowed_file_extensions": ["txt", "pdf"]},
    )
    assert g.status_code == 200
