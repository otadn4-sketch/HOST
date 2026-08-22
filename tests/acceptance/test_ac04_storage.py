from tests.conftest import auth_header, login, seed_user


def test_ac04_download_hides_path(client):
    seed_user("alice", "user")
    login(client, "alice")
    h = auth_header(client)
    up = client.post(
        "/api/files",
        headers=h,
        files={"file": ("ok.txt", b"payload-bytes\n", "text/plain")},
        data={"title": "دریافت", "topic": "آزمون", "classification": "internal"},
    )
    body = up.json()["file"]
    assert "storage_relpath" not in body
    assert "/" not in body["stored_vault_name"]
    assert "\\" not in body["stored_vault_name"]
    if body["scan_status"] == "clean":
        dl = client.get(f"/api/files/{body['id']}/download", headers=h)
        assert dl.status_code == 200
        assert dl.content == b"payload-bytes\n"
        assert "Content-Disposition" in dl.headers
