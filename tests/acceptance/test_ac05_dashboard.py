from tests.conftest import auth_header, login, seed_user


def test_ac05_dashboard_admin_only(client):
    seed_user("admin", "system_admin")
    seed_user("mgr", "group_admin", email="mgr@eytan.local")
    login(client, "admin")
    h = auth_header(client)
    res = client.get("/api/dashboard?range=week", headers=h)
    assert res.status_code == 200
    data = res.json()
    assert "kpis" in data
    assert "users_total" in data["kpis"]
    assert "events" in data
    client.post("/api/auth/logout", headers=h)
    login(client, "mgr")
    hm = auth_header(client)
    assert client.get("/api/dashboard", headers=hm).status_code == 403
