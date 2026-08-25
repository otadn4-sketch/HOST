from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "reset-data.sh"


def test_reset_data_script_refuses_without_explicit_flag():
    proc = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, check=False)
    assert proc.returncode == 2
    combined = proc.stdout + proc.stderr
    assert "--i-understand-this-deletes-all-users-and-files" in combined
    assert "RESET-EYTAN-DATA" in combined


def test_reset_data_script_dry_run_does_not_delete():
    proc = subprocess.run(["bash", str(SCRIPT), "--dry-run"], capture_output=True, text=True, check=False)
    assert proc.returncode == 0
    assert "nothing deleted" in proc.stdout
    assert "pgdata" in proc.stdout or "Docker is not installed" in proc.stdout


def test_create_admin_script_prompts_for_password_and_does_not_hardcode_it():
    text = (ROOT / "scripts" / "create-admin.sh").read_text(encoding="utf-8")
    assert 'read -r -p "username: " USERNAME' in text
    assert 'read -r -p "full name: " FULL_NAME' in text
    assert 'read -r -p "email: " EMAIL' in text
    assert 'read -r -s -p "password: " PASSWORD' in text
    assert '--password "$PASSWORD"' in text
    assert 'read -r -p "username: " admin' not in text
    assert "change-me" not in text.lower()
    assert "Str0ng-Passw0rd" not in text
