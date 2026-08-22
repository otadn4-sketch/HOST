import zipfile
from pathlib import Path

from tests.conftest import auth_header, login, seed_user


def test_update_confirm_installs_and_blocks_second_success(client, tmp_path, monkeypatch):
    live = tmp_path / "live"
    (live / "app").mkdir(parents=True)
    (live / "app" / "old.py").write_text("old")
    frontend = tmp_path / "frontend-overlay"
    frontend.mkdir()
    monkeypatch.setenv("EYTAN_APP_ROOT", str(live))
    monkeypatch.setenv("OVERLAY_FRONTEND_PATH", str(frontend))

    seed_user("admin", "system_admin")
    login(client, "admin")
    h = auth_header(client)

    zpath = tmp_path / "src.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("HOST/VERSION", "1.2.1\n")
        zf.writestr("HOST/backend/app/hello.py", "x = 1\n")
        zf.writestr("HOST/frontend/dist/index.html", "<html>ok</html>")
        zf.writestr("HOST/docker-compose.yml", "services: {}\n")
        zf.writestr("HOST/install.sh", "#!/bin/sh\necho pwn\n")

    with zpath.open("rb") as fh:
        uploaded = client.post(
            "/api/updates/upload",
            headers=h,
            files={"file": ("proj.zip", fh, "application/zip")},
        )
    assert uploaded.status_code == 200, uploaded.text
    body = uploaded.json()["update"]
    assert body["status"] == "validated", body
    uid = body["id"]

    installed = client.post(f"/api/updates/{uid}/confirm", headers=h)
    assert installed.status_code == 200, installed.text
    assert installed.json()["ok"] is True
    assert (live / "app" / "hello.py").read_text() == "x = 1\n"
    assert (frontend / "index.html").read_text() == "<html>ok</html>"
    listed = client.get("/api/updates", headers=h).json()["updates"]
    row = next(item for item in listed if item["id"] == uid)
    assert row["status"] == "success"

    second = client.post(f"/api/updates/{uid}/confirm", headers=h)
    assert second.status_code == 400
    assert "قابل نصب نیست" in second.json()["detail"]
