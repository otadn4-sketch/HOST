import json
import zipfile
from pathlib import Path

from nacl.signing import SigningKey

from app.services.release_bundle import verify_and_extract


def _bundle(tmp_path: Path, sk: SigningKey, extra_name: str | None = None, bad_hash=False) -> Path:
    payload = tmp_path / "payload"
    (payload / "frontend").mkdir(parents=True)
    (payload / "frontend" / "index.html").write_text("<html></html>")
    files = [{"path": "frontend/index.html", "sha256": __import__("hashlib").sha256(b"<html></html>").hexdigest(), "size": len("<html></html>")}]
    if bad_hash:
        files[0]["sha256"] = "0" * 64
    manifest = {
        "version": "1.0.1",
        "compatible_from": "1.0.0",
        "migration_id": "001_initial",
        "changelog": "fix",
        "files": files,
    }
    canonical = json.dumps({k: v for k, v in manifest.items()}, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    manifest["signature"] = sk.sign(canonical).signature.hex()
    zpath = tmp_path / "r.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.write(payload / "frontend" / "index.html", "frontend/index.html")
        if extra_name:
            zf.writestr(extra_name, "#!/bin/sh\necho pwn")
    return zpath


def test_valid_bundle(tmp_path: Path):
    sk = SigningKey.generate()
    z = _bundle(tmp_path, sk)
    dest = tmp_path / "out"
    result = verify_and_extract(z, sk.verify_key.encode().hex(), dest)
    assert result.ok, result.errors


def test_rejects_install_sh(tmp_path: Path):
    sk = SigningKey.generate()
    z = _bundle(tmp_path, sk, extra_name="install.sh")
    result = verify_and_extract(z, sk.verify_key.encode().hex(), tmp_path / "out2")
    assert not result.ok
    assert any("forbidden" in e or "not allowed" in e for e in result.errors)


def test_rejects_compose(tmp_path: Path):
    sk = SigningKey.generate()
    z = _bundle(tmp_path, sk, extra_name="docker-compose.yml")
    result = verify_and_extract(z, sk.verify_key.encode().hex(), tmp_path / "out3")
    assert not result.ok


def test_rejects_bad_signature(tmp_path: Path):
    sk = SigningKey.generate()
    other = SigningKey.generate()
    z = _bundle(tmp_path, sk)
    result = verify_and_extract(z, other.verify_key.encode().hex(), tmp_path / "out4")
    assert not result.ok


def test_rejects_hash_mismatch(tmp_path: Path):
    sk = SigningKey.generate()
    z = _bundle(tmp_path, sk, bad_hash=True)
    result = verify_and_extract(z, sk.verify_key.encode().hex(), tmp_path / "out5")
    assert not result.ok


def test_accepts_nested_source_zip_without_manifest(tmp_path: Path):
    root = tmp_path / "proj"
    (root / "backend" / "app").mkdir(parents=True)
    (root / "backend" / "app" / "hello.py").write_text("x = 1\n")
    (root / "VERSION").write_text("1.1.0\n")
    (root / "docker-compose.yml").write_text("services: {}\n")
    zpath = tmp_path / "src.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.write(root / "VERSION", "HOST-folder/VERSION")
        zf.write(root / "backend" / "app" / "hello.py", "HOST-folder/backend/app/hello.py")
        zf.write(root / "docker-compose.yml", "HOST-folder/docker-compose.yml")
    dest = tmp_path / "out-src"
    result = verify_and_extract(zpath, "", dest, allow_unsigned=True)
    assert result.ok, result.errors
    assert (dest / "VERSION").read_text().strip() == "1.1.0"
    assert (dest / "backend" / "app" / "hello.py").exists()
    assert not (dest / "docker-compose.yml").exists()
    assert result.manifest["version"] == "1.1.0"


def test_nested_signed_manifest_is_found(tmp_path: Path):
    sk = SigningKey.generate()
    inner = _bundle(tmp_path, sk)
    nested = tmp_path / "nested.zip"
    with zipfile.ZipFile(inner) as src, zipfile.ZipFile(nested, "w") as dst:
        for info in src.infolist():
            dst.writestr("eytan-1.1.0/" + info.filename, src.read(info.filename))
    dest = tmp_path / "out-nested"
    result = verify_and_extract(nested, sk.verify_key.encode().hex(), dest, allow_unsigned=True)
    assert result.ok, result.errors
    assert (dest / "frontend" / "index.html").exists()
