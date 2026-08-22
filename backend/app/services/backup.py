from __future__ import annotations

import hashlib
import json
import os
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import Settings


def _key_from_hex(value: str) -> bytes:
    raw = (value or "").strip()
    if len(raw) == 64:
        return bytes.fromhex(raw)
    if len(raw) >= 32:
        return hashlib.sha256(raw.encode("utf-8")).digest()
    raise ValueError("BACKUP_ENCRYPTION_KEY is missing or too short")


def create_backup(settings: Settings, db_dump: bytes, note: str = "") -> Path:
    settings.backup_path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    staging = Path(tempfile.mkdtemp(prefix="eytan-bak-"))
    archive_path = staging / "payload.tar"
    with tarfile.open(archive_path, "w") as tar:
        dump_file = staging / "db.dump"
        dump_file.write_bytes(db_dump)
        tar.add(dump_file, arcname="db.dump")
        vault = settings.vault_path
        if vault.exists():
            tar.add(vault, arcname="vault")
        meta = staging / "meta.json"
        meta.write_text(json.dumps({"note": note, "created_at": stamp}, ensure_ascii=False), encoding="utf-8")
        tar.add(meta, arcname="meta.json")

    payload = archive_path.read_bytes()
    key = _key_from_hex(settings.backup_encryption_key)
    aes = AESGCM(key)
    nonce = os.urandom(12)
    token = nonce + aes.encrypt(nonce, payload, b"eytan-backup-v1")
    dest = settings.backup_path / f"eytan-backup-{stamp}.bin"
    dest.write_bytes(token)
    return dest


def restore_backup(settings: Settings, archive: Path, dest_vault: Path) -> bytes:
    blob = archive.read_bytes()
    nonce, ciphertext = blob[:12], blob[12:]
    key = _key_from_hex(settings.backup_encryption_key)
    payload = AESGCM(key).decrypt(nonce, ciphertext, b"eytan-backup-v1")
    staging = Path(tempfile.mkdtemp(prefix="eytan-restore-"))
    tar_path = staging / "payload.tar"
    tar_path.write_bytes(payload)
    extract_to = staging / "extracted"
    extract_to.mkdir()
    with tarfile.open(tar_path, "r") as tar:
        def is_safe(member: tarfile.TarInfo) -> bool:
            name = member.name.replace("\\", "/")
            if name.startswith("/") or ".." in Path(name).parts:
                return False
            if member.issym() or member.islnk():
                return False
            return True

        members = [m for m in tar.getmembers() if is_safe(m)]
        tar.extractall(extract_to, members=members, filter="data")
    dump = (extract_to / "db.dump").read_bytes()
    src_vault = extract_to / "vault"
    if src_vault.exists():
        dest_vault.mkdir(parents=True, exist_ok=True)
        _copytree_replace(src_vault, dest_vault)
    return dump


def _copytree_replace(src: Path, dest: Path) -> None:
    import shutil

    if dest.exists():
        for child in dest.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    shutil.copytree(src, dest, dirs_exist_ok=True)
