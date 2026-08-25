#!/usr/bin/env bash
# Destructive, opt-in wipe of application users, database, vault, quarantine,
# and local encrypted backups. Does not delete source, .env, TLS certs,
# ClamAV signatures, or the live_app / live_frontend code volumes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CONFIRMATION_PHRASE="RESET-EYTAN-DATA"
REQUIRED_FLAG="--i-understand-this-deletes-all-users-and-files"
DRY_RUN=0
CONFIRMED_FLAG=0

usage() {
  cat <<EOF
Usage:
  $0 --dry-run
  $0 ${REQUIRED_FLAG}

This permanently deletes users, files, audit logs, vault contents,
quarantine, and local encrypted backups on this Docker stack.

It does NOT delete:
  source code, .env, TLS certificates, ClamAV signature DB,
  live_app / live_frontend (running code), staging, releases.

After a successful wipe, create a new admin:
  ./scripts/create-admin.sh

Non-interactive confirmation:
  EYTAN_CONFIRM_RESET=${CONFIRMATION_PHRASE} $0 ${REQUIRED_FLAG}
EOF
}

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --help|-h) usage; exit 0 ;;
    "$REQUIRED_FLAG") CONFIRMED_FLAG=1 ;;
    *)
      echo "unknown argument: $arg" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ "$DRY_RUN" != "1" && "$CONFIRMED_FLAG" != "1" ]]; then
  usage
  exit 2
fi

if [[ ! -f docker-compose.yml ]]; then
  echo "این پوشه پروژه سامانه نیست (docker-compose.yml پیدا نشد)."
  exit 1
fi

volume_for() {
  local service="$1"
  local destination="$2"
  local id
  id="$(docker compose ps -aq "$service" 2>/dev/null | head -n1 || true)"
  if [[ -z "$id" ]]; then
    return 0
  fi
  docker inspect -f "{{range .Mounts}}{{if eq .Destination \"${destination}\"}}{{.Name}}{{end}}{{end}}" "$id" 2>/dev/null || true
}

project_name() {
  local name=""
  if command -v docker >/dev/null 2>&1; then
    name="$(docker compose config --format json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("name",""))' 2>/dev/null || true)"
    if [[ -z "$name" ]]; then
      name="$(docker compose ls --format json 2>/dev/null | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(rows[0]["Name"] if rows else "")' 2>/dev/null || true)"
    fi
  fi
  if [[ -z "$name" ]]; then
    name="$(basename "$ROOT" | tr '[:upper:]' '[:lower:]')"
  fi
  printf '%s' "$name"
}

TARGETS=()
add_target() {
  local name="$1"
  [[ -n "$name" ]] || return 0
  local existing
  for existing in "${TARGETS[@]+"${TARGETS[@]}"}"; do
    if [[ "$existing" == "$name" ]]; then
      return 0
    fi
  done
  TARGETS+=("$name")
}

DOCKER_OK=0
if command -v docker >/dev/null 2>&1; then
  DOCKER_OK=1
  add_target "$(volume_for db /var/lib/postgresql/data)"
  add_target "$(volume_for backend /var/lib/eytan/vault)"
  add_target "$(volume_for backend /var/lib/eytan/quarantine)"
  add_target "$(volume_for backend /var/lib/eytan/backups)"
  PROJECT="$(project_name)"
  add_target "${PROJECT}_pgdata"
  add_target "${PROJECT}_vault"
  add_target "${PROJECT}_quarantine"
  add_target "${PROJECT}_backups"
fi

LOCAL_DIRS=(
  "$ROOT/data/vault"
  "$ROOT/data/quarantine"
  "$ROOT/data/backups"
)

echo "This will permanently delete application data on this host:"
echo "  - PostgreSQL volume (users, files metadata, audit logs)"
echo "  - vault files"
echo "  - quarantine"
echo "  - local encrypted backups (BACKUP_PATH volume / data/backups)"
echo "Kept: source, .env, TLS certs, ClamAV DB, live_app, live_frontend, staging, releases."
echo
if [[ "$DOCKER_OK" == "1" ]]; then
  echo "Docker volumes to remove:"
  if [[ ${#TARGETS[@]} -eq 0 ]]; then
    echo "  (none discovered yet; compose names will still be attempted)"
  else
    for vol in "${TARGETS[@]}"; do
      echo "  - $vol"
    done
  fi
else
  echo "Docker is not installed in this environment; compose volumes cannot be removed here."
fi
echo "Local directories to empty:"
for dir in "${LOCAL_DIRS[@]}"; do
  echo "  - $dir"
done
echo "External BACKUP_EXTERNAL_PATH is not touched automatically."

if [[ "$DRY_RUN" == "1" ]]; then
  echo "dry-run only; nothing deleted."
  exit 0
fi

got="${EYTAN_CONFIRM_RESET:-}"
if [[ -z "$got" ]]; then
  read -r -p "Type ${CONFIRMATION_PHRASE} to continue: " got
fi
if [[ "$got" != "$CONFIRMATION_PHRASE" ]]; then
  echo "aborted."
  exit 1
fi

if [[ "$DOCKER_OK" == "1" ]]; then
  echo "Stopping stack so data volumes can be removed..."
  docker compose down
  for vol in "${TARGETS[@]}"; do
    if docker volume inspect "$vol" >/dev/null 2>&1; then
      echo "Removing volume: $vol"
      docker volume rm -f "$vol"
    fi
  done
else
  echo "Docker is missing; compose volumes were not removed."
fi

for dir in "${LOCAL_DIRS[@]}"; do
  mkdir -p "$dir"
  # Remove contents, keep the directory.
  find "$dir" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
  echo "Emptied $dir"
done

if [[ "$DOCKER_OK" == "1" ]]; then
  echo "Starting empty stack..."
  docker compose up -d
  echo "waiting for backend health..."
  ok=0
  for i in $(seq 1 60); do
    if docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')" >/dev/null 2>&1; then
      ok=1
      break
    fi
    sleep 2
  done
  if [[ "$ok" != "1" ]]; then
    echo "Backend did not become healthy. Logs:"
    docker compose logs --tail=80 backend || true
    exit 1
  fi
  echo "Data wipe complete. Create a new admin:"
  echo "  ./scripts/create-admin.sh"
else
  echo "Local folders emptied. Install Docker on the machine that runs the stack and re-run this script there."
  exit 1
fi
