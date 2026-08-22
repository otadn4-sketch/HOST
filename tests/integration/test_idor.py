from tests.conftest import auth_header, login, seed_user


def test_idor_group_and_log_ids(client):
    seed_user("admin", "system_admin")
    seed_user("alice", "user", email="alice@eytan.local")
    login(client, "admin")
    ha = auth_header(client)
    groups = client.get("/api/groups", headers=ha).json()["groups"]
    other = next(g for g in groups if g["code"] != "SEC-IT")
    logs = client.get("/api/logs", headers=ha).json()["logs"]
    log_id = logs[0]["id"]
    client.post("/api/auth/logout", headers=ha)

    login(client, "alice")
    h = auth_header(client)
    assert client.get(f"/api/groups/{other['id']}", headers=h).status_code == 404
    assert client.get(f"/api/logs?log_id={log_id}", headers=h).status_code in {403, 404}
    assert client.get("/api/updates", headers=h).status_code == 403
    users = client.get("/api/users").json()["users"]
    # alice can only see herself via list
    assert all(u["username"] == "alice" for u in users)
