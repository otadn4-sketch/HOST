#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# Restore is explicit and never targets the live vault unless you override after review.
# Required:
#   DB_ARCHIVE=path/to/eytan-db-....bin
#   VAULT_ARCHIVE=path/to/eytan-vault-....bin
#   DEST_VAULT=path/to/empty-restore-dir
#   DEST_DB=path/to/restored.dump
DB_ARCHIVE="${DB_ARCHIVE:?set DB_ARCHIVE to the encrypted database backup}"
VAULT_ARCHIVE="${VAULT_ARCHIVE:?set VAULT_ARCHIVE to the encrypted vault backup}"
DEST_VAULT="${DEST_VAULT:?set DEST_VAULT to a directory other than the live vault}"
DEST_DB="${DEST_DB:-./restored-db.dump}"

run_cli() {
  if command -v docker >/dev/null 2>&1 && docker compose ps --status running --services 2>/dev/null | grep -qx backend; then
    docker compose exec -T backend python -m app.cli "$@"
  else
    PYTHONPATH="${PYTHONPATH:-}:backend" python3 -m app.cli "$@"
  fi
}

run_cli restore-db --archive "$DB_ARCHIVE" --out "$DEST_DB"
run_cli restore-vault --archive "$VAULT_ARCHIVE" --dest "$DEST_VAULT"
echo "Decrypted dump: $DEST_DB"
echo "Restored vault files: $DEST_VAULT"
echo "Live PostgreSQL was not changed. To load the dump into a *separate* database, use pg_restore against that database only."
