from pathlib import Path

from app.config import Settings
from app.services.backup import create_backup, restore_backup


def test_backup_roundtrip(tmp_path: Path, monkeypatch):
    settings = Settings(
        backup_encryption_key="ab" * 32,
        vault_path=tmp_path / "vault",
        backup_path=tmp_path / "bak",
    )
    settings.vault_path.mkdir()
    (settings.vault_path / "file1").write_text("secret-bytes")
    archive = create_backup(settings, b"PGDUMP", note="test")
    dest = tmp_path / "restored"
    dump = restore_backup(settings, archive, dest)
    assert dump == b"PGDUMP"
    assert (dest / "file1").read_text() == "secret-bytes"
