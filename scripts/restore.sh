#!/usr/bin/env bash
set -euo pipefail
# Restore is intentionally explicit. See docs/backup-recovery.md
echo "Use docs/backup-recovery.md. Example:"
echo "  docker compose exec -T db pg_restore --clean --if-exists -U eytan -d eytan < backup.dump"
echo "  then restore the encrypted vault bundle with the Python restore helper."
exit 1
