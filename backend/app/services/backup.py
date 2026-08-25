from __future__ import annotations

import hashlib
import json
import os
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import Settings


WEAK_BACKUP_KEYS = {
    "",
    "change-me-64-hex-chars",
    "change-me-in-production",
    "0" * 64,
    "1" * 64,
    "a" * 64,
    "f" * 64,
}

AAD_DB = b"eytan-db-backup-v1"
AAD_VAULT = b"eytan-vault-backup-v1"


def require_backup_key(value: str, *, production: bool = False) -> bytes:
    raw = (value or "").strip()
    if raw in WEAK_BACKUP_KEYS or raw.lower() in WEAK_BACKUP_KEYS:
        raise ValueError("BACKUP_ENCRYPTION_KEY is missing, weak, or a sample placeholder")
    if len(raw) != 64:
        raise ValueError("BACKUP_ENCRYPTION_KEY must be 64 hex characters")
    try:
        key = bytes.fromhex(raw)
    except ValueError as exc:
        raise ValueError("BACKUP_ENCRYPTION_KEY must be hexadecimal") from exc
    if production and len(set(key)) < 8:
        raise ValueError("BACKUP_ENCRYPTION_KEY entropy is too low for production")
    return key


def backup_path_is_isolated(settings: Settings) -> bool:
    backup = settings.backup_path.resolve()
    vault = settings.vault_path.resolve()
    quarantine = settings.quarantine_path.resolve()
    if backup == vault or backup == quarantine:
        return False
    try:
        backup.relative_to(vault)
        return False
    except ValueError:
        return True


def _encrypt(payload: bytes, key: bytes, aad: bytes) -> bytes:
    nonce = os.urandom(12)
    token = AESGCM(key).encrypt(nonce, payload, aad)
    return nonce + token


def _decrypt(blob: bytes, key: bytes, aad: bytes) -> bytes:
    if len(blob) < 13:
        raise ValueError("backup blob is truncated")
    nonce, ciphertext = blob[:12], blob[12:]
    return AESGCM(key).decrypt(nonce, ciphertext, aad)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@dataclass
class BackupPair:
    db_archive: Path
    vault_archive: Path
    created_at: str


def create_database_backup(settings: Settings, db_dump: bytes, note: str = "") -> Path:
    if not backup_path_is_isolated(settings):
        raise ValueError("BACKUP_PATH must be outside the vault and quarantine directories")
    key = require_backup_key(settings.backup_encryption_key, production=settings.is_production)
    settings.backup_path.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    envelope = {
        "kind": "database",
        "created_at": stamp,
        "note": note,
        "sha256": hashlib.sha256(db_dump).hexdigest(),
        "size": len(db_dump),
    }
    packed = json.dumps(envelope, ensure_ascii=False).encode("utf-8") + b"\n" + db_dump
    dest = settings.backup_path / f"eytan-db-{stamp}.bin"
    dest.write_bytes(_encrypt(packed, key, AAD_DB))
    return dest


def create_vault_backup(settings: Settings, note: str = "") -> Path:
    if not backup_path_is_isolated(settings):
        raise ValueError("BACKUP_PATH must be outside the vault and quarantine directories")
    key = require_backup_key(settings.backup_encryption_key, production=settings.is_production)
    settings.backup_path.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    staging = Path(tempfile.mkdtemp(prefix="eytan-vault-bak-"))
    archive_path = staging / "vault.tar"
    with tarfile.open(archive_path, "w") as tar:
        vault = settings.vault_path
        if vault.exists():
            tar.add(vault, arcname="vault")
        meta = staging / "meta.json"
        meta.write_text(
            json.dumps({"kind": "vault", "note": note, "created_at": stamp}, ensure_ascii=False),
            encoding="utf-8",
        )
        tar.add(meta, arcname="meta.json")
    dest = settings.backup_path / f"eytan-vault-{stamp}.bin"
    dest.write_bytes(_encrypt(archive_path.read_bytes(), key, AAD_VAULT))
    return dest


def create_backup(settings: Settings, db_dump: bytes, note: str = "") -> BackupPair:
    """Create separate encrypted database and vault backups. Does not modify source data."""
    stamp_note = note or "manual"
    db_archive = create_database_backup(settings, db_dump, note=stamp_note)
    vault_archive = create_vault_backup(settings, note=stamp_note)
    return BackupPair(db_archive=db_archive, vault_archive=vault_archive, created_at=_stamp())


def restore_database_backup(settings: Settings, archive: Path) -> bytes:
    key = require_backup_key(settings.backup_encryption_key, production=settings.is_production)
    packed = _decrypt(archive.read_bytes(), key, AAD_DB)
    header, sep, dump = packed.partition(b"\n")
    if not sep:
        raise ValueError("database backup envelope is invalid")
    meta = json.loads(header.decode("utf-8"))
    expected = meta.get("sha256")
    if expected and hashlib.sha256(dump).hexdigest() != expected:
        raise ValueError("database dump hash mismatch")
    return dump


def restore_vault_backup(settings: Settings, archive: Path, dest_vault: Path) -> None:
    """Restore vault files into dest_vault. Never writes into the live vault unless dest_vault is that path."""
    key = require_backup_key(settings.backup_encryption_key, production=settings.is_production)
    payload = _decrypt(archive.read_bytes(), key, AAD_VAULT)
    staging = Path(tempfile.mkdtemp(prefix="eytan-restore-vault-"))
    tar_path = staging / "vault.tar"
    tar_path.write_bytes(payload)
    extract_to = staging / "extracted"
    extract_to.mkdir()
    with tarfile.open(tar_path, "r") as tar:
        members = [m for m in tar.getmembers() if _safe_tar_member(m)]
        tar.extractall(extract_to, members=members, filter="data")
    src_vault = extract_to / "vault"
    dest_vault.mkdir(parents=True, exist_ok=True)
    if src_vault.exists():
        _copy_into(src_vault, dest_vault)


def restore_backup(settings: Settings, archive: Path, dest_vault: Path) -> bytes:
    """Backward-compatible helper: database archives return dump bytes; vault archives restore files."""
    name = archive.name
    if "vault" in name:
        restore_vault_backup(settings, archive, dest_vault)
        return b""
    return restore_database_backup(settings, archive)


def _safe_tar_member(member: tarfile.TarInfo) -> bool:
    name = member.name.replace("\\", "/")
    if name.startswith("/") or ".." in Path(name).parts:
        return False
    if member.issym() or member.islnk():
        return False
    return True


def _copy_into(src: Path, dest: Path) -> None:
    import shutil

    dest.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        target = dest / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
