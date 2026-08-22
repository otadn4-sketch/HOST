from tests.conftest import auth_header, login, seed_user


def test_ac07_audit_append_only_and_policy(client):
    seed_user("admin", "system_admin")
    login(client, "admin")
    h = auth_header(client)
    logs = client.get("/api/logs", headers=h)
    assert logs.status_code == 200
    assert logs.json()["logs"]
    # no update endpoint
    log_id = logs.json()["logs"][0]["id"]
    assert client.put(f"/api/logs/{log_id}", headers=h, json={"details": "hack"}).status_code in {404, 405, 403}
    assert client.delete(f"/api/logs/{log_id}", headers=h).status_code in {404, 405, 403}
    pol = client.put(
        "/api/settings/policy",
        headers=h,
        json={"allowed_extensions": ["txt", "pdf"], "max_file_size_bytes": 10_000_000},
    )
    assert pol.status_code == 200
    assert "exe" not in pol.json()["policy"]["allowed_extensions"]
    denied = client.put("/api/settings/policy", headers=h, json={"allowed_extensions": ["pdf", "exe"]})
    assert denied.status_code == 400
