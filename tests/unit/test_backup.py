from pathlib import Path

from app.config import Settings
from app.services.backup import (
    create_backup,
    require_backup_key,
    restore_database_backup,
    restore_vault_backup,
)
import pytest


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        eytan_env="development",
        backup_encryption_key="ab" * 32,
        vault_path=tmp_path / "vault",
        backup_path=tmp_path / "backups",
        quarantine_path=tmp_path / "quarantine",
    )


def test_backup_roundtrip_separate_encrypted_archives(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.vault_path.mkdir()
    (settings.vault_path / "file1").write_text("secret-bytes")
    live_before = (settings.vault_path / "file1").read_text()
    pair = create_backup(settings, b"PGDUMP", note="test")
    assert pair.db_archive.name.startswith("eytan-db-")
    assert pair.vault_archive.name.startswith("eytan-vault-")
    assert pair.db_archive.parent == settings.backup_path
    assert pair.db_archive.parent != settings.vault_path
    dump = restore_database_backup(settings, pair.db_archive)
    dest = tmp_path / "restored-vault"
    restore_vault_backup(settings, pair.vault_archive, dest)
    assert dump == b"PGDUMP"
    assert (dest / "file1").read_text() == "secret-bytes"
    assert (settings.vault_path / "file1").read_text() == live_before


def test_restore_does_not_modify_live_vault(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.vault_path.mkdir()
    (settings.vault_path / "keep.txt").write_text("live")
    pair = create_backup(settings, b"DUMP")
    (settings.vault_path / "keep.txt").write_text("changed-live")
    restore_vault_backup(settings, pair.vault_archive, tmp_path / "out")
    assert (settings.vault_path / "keep.txt").read_text() == "changed-live"


def test_weak_backup_key_rejected():
    with pytest.raises(ValueError):
        require_backup_key("change-me-64-hex-chars", production=True)
    with pytest.raises(ValueError):
        require_backup_key("0" * 64, production=True)
    with pytest.raises(ValueError):
        require_backup_key("short", production=False)


def test_wrong_key_cannot_restore(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.vault_path.mkdir()
    (settings.vault_path / "file1").write_text("secret-bytes")
    pair = create_backup(settings, b"PGDUMP")
    settings.backup_encryption_key = "cd" * 32
    with pytest.raises(Exception):
        restore_database_backup(settings, pair.db_archive)
