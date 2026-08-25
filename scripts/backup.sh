#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# Encrypted, split backups. Does not delete or reset live data.
if command -v docker >/dev/null 2>&1 && docker compose ps --status running --services 2>/dev/null | grep -qx backend; then
  docker compose exec -T backend python -m app.cli backup --note "scripted"
else
  PYTHONPATH="${PYTHONPATH:-}:backend" python3 -m app.cli backup --note "scripted"
fi
