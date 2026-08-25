from tests.conftest import STRONG, auth_header, login, seed_user


def test_ac01_login_logout_and_lockout(client):
    seed_user("admin", "system_admin")
    bad = client.post("/api/auth/login", json={"username": "admin", "password": "wrong-Wrong-1"})
    assert bad.status_code == 401
    ok = login(client, "admin")
    assert ok.status_code == 200
    assert "eytan_session" in ok.cookies
    assert ok.json()["user"]["role"] == "system_admin"
    headers = auth_header(client)
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    out = client.post("/api/auth/logout", headers=headers)
    assert out.status_code == 200
    me2 = client.get("/api/auth/me")
    assert me2.status_code == 401

    seed_user("lockme", "user", email="lockme@eytan.local")
    last = None
    for _ in range(5):
        last = client.post("/api/auth/login", json={"username": "lockme", "password": "Nope-Nope-No1"})
    assert last.status_code in {401, 423}
    locked = client.post("/api/auth/login", json={"username": "lockme", "password": STRONG})
    assert locked.status_code == 423


def test_ac01_login_accepts_username_case_and_spaces(client):
    seed_user("ArchiveAdmin", "system_admin", email="archive-admin@eytan.local")
    ok = login(client, "  archiveadmin  ")
    assert ok.status_code == 200
    assert ok.json()["user"]["username"] == "ArchiveAdmin"
