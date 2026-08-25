import hashlib
import json
import zipfile

from nacl.signing import SigningKey

from app.config import get_settings
from tests.conftest import auth_header, login, seed_user


def _signed_zip(tmp_path, sk: SigningKey, version: str = "1.5.0"):
    files = {
        "VERSION": f"{version}\n",
        "backend/app/hello.py": "x = 1\n",
        "frontend/index.html": "<html>ok</html>",
    }
    listed = []
    for path, content in files.items():
        data = content.encode()
        listed.append({"path": path, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
    manifest = {
        "version": version,
        "compatible_from": "0.0.0",
        "migration_id": "",
        "changelog": "signed test bundle",
        "files": listed,
    }
    canonical = json.dumps({k: v for k, v in manifest.items()}, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    manifest["signature"] = sk.sign(canonical).signature.hex()
    zpath = tmp_path / "signed.eytan.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        for path, content in files.items():
            zf.writestr(path, content)
    return zpath


def test_unsigned_update_rejected(client, tmp_path):
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
    assert body["status"] == "rejected"
    confirm = client.post(f"/api/updates/{body['id']}/confirm", headers=h)
    assert confirm.status_code == 400


def test_signed_update_without_public_key_rejected(client, tmp_path):
    seed_user("admin", "system_admin")
    login(client, "admin")
    h = auth_header(client)
    sk = SigningKey.generate()
    get_settings().update_public_key = ""
    zpath = _signed_zip(tmp_path, sk)
    with zpath.open("rb") as fh:
        uploaded = client.post(
            "/api/updates/upload",
            headers=h,
            files={"file": ("rel.eytan.zip", fh, "application/zip")},
        )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["update"]["status"] == "rejected"
    assert "UPDATE_PUBLIC_KEY" in (uploaded.json()["update"].get("error") or "")


def test_signed_update_confirm_installs_and_blocks_second_success(client, tmp_path, monkeypatch):
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

    sk = SigningKey.generate()
    get_settings().update_public_key = sk.verify_key.encode().hex()
    zpath = _signed_zip(tmp_path, sk, version="1.5.1")

    with zpath.open("rb") as fh:
        uploaded = client.post(
            "/api/updates/upload",
            headers=h,
            files={"file": ("rel.eytan.zip", fh, "application/zip")},
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
