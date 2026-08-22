#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  rand() { python3 -c "import secrets; print(secrets.token_urlsafe(48))"; }
  hex32() { python3 -c "import secrets; print(secrets.token_hex(32))"; }
  pw="$(rand)"
  sess="$(rand)"
  upd="$(rand)"
  bak="$(hex32)"
  python3 - <<PY
from pathlib import Path
p = Path(".env")
t = p.read_text()
t = t.replace("POSTGRES_PASSWORD=change-me-with-a-long-random-value", "POSTGRES_PASSWORD=${pw}")
t = t.replace("eytan:change-me-with-a-long-random-value@", "eytan:${pw}@")
t = t.replace("SESSION_SECRET=change-me-with-a-long-random-value", "SESSION_SECRET=${sess}")
t = t.replace("UPDATE_AGENT_TOKEN=change-me-with-a-long-random-value", "UPDATE_AGENT_TOKEN=${upd}")
t = t.replace("BACKUP_ENCRYPTION_KEY=change-me-64-hex-chars", "BACKUP_ENCRYPTION_KEY=${bak}")
p.write_text(t)
print("generated secrets in .env")
PY
fi

mkdir -p infra/nginx/certs data/vault data/quarantine data/backups
if [[ ! -f infra/nginx/certs/fullchain.pem ]]; then
  openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
    -keyout infra/nginx/certs/privkey.pem \
    -out infra/nginx/certs/fullchain.pem \
    -subj "/CN=${PUBLIC_HOST:-localhost}" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
  echo "created self-signed TLS material in infra/nginx/certs (replace with a real certificate for production)"
fi

chmod 600 infra/nginx/certs/privkey.pem || true
docker compose up -d --build
echo "waiting for backend health..."
for i in $(seq 1 60); do
  if docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')" >/dev/null 2>&1; then
    echo "backend is healthy"
    break
  fi
  sleep 2
done
echo "bootstrap complete. create the first admin with: ./scripts/create-admin.sh"
