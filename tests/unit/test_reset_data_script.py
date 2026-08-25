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
