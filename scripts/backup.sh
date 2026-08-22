#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
docker compose exec -T backend python - <<'PY'
from app.config import get_settings
from app.services.backup import create_backup
from sqlalchemy import create_engine, text
settings = get_settings()
# Logical dump of operational tables as SQL is handled by pg_dump in production.
# This helper stores an application-level encrypted bundle of vault + marker.
create_backup(settings, b"use-pg-dump", note="wrapper")
print("encrypted backup written to", settings.backup_path)
PY
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-eytan}" -d "${POSTGRES_DB:-eytan}" -Fc > /tmp/eytan-db.dump
echo "database dump written to host /tmp/eytan-db.dump — copy it to the separate backup disk and encrypt with scripts in docs/backup-recovery.md"
