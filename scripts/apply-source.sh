#!/usr/bin/env bash
# Apply the source in this folder to the running Docker stack.
# Keeps database, vault, and uploaded files. Rebuilds only application code.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f docker-compose.yml ]]; then
  echo "این پوشه پروژه سامانه نیست (docker-compose.yml پیدا نشد)."
  exit 1
fi
if [[ ! -f .env ]]; then
  echo "فایل .env نیست. آن را از نصب قبلی کپی کنید و bootstrap.sh را دوباره اجرا نکنید."
  exit 1
fi
if ! command -v docker >/dev/null; then
  echo "Docker نصب نیست."
  exit 1
fi

echo "کد همین پوشه روی کانتینرها اعمال می‌شود."
echo "دیتابیس، والت و فایل‌های بارگذاری‌شده نگه داشته می‌شوند."
echo "volumeهای live_app و live_frontend حذف می‌شوند چون کد قدیمی را قفل کرده‌اند."

backend_id="$(docker compose ps -aq backend 2>/dev/null | head -n1 || true)"
frontend_id="$(docker compose ps -aq frontend 2>/dev/null | head -n1 || true)"
live_app=""
live_fe=""
if [[ -n "$backend_id" ]]; then
  live_app="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/app"}}{{.Name}}{{end}}{{end}}' "$backend_id" 2>/dev/null || true)"
fi
if [[ -n "$frontend_id" ]]; then
  live_fe="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/usr/share/nginx/html"}}{{.Name}}{{end}}{{end}}' "$frontend_id" 2>/dev/null || true)"
fi

echo "در حال ساخت ایمیج از سورس فعلی..."
docker compose build backend frontend update-agent

echo "توقف سرویس‌های برنامه..."
docker compose stop backend frontend update-agent nginx 2>/dev/null || true
docker compose rm -f backend frontend update-agent 2>/dev/null || true

if [[ -n "$live_app" ]]; then
  echo "حذف volume کد بک‌اند: $live_app"
  docker volume rm -f "$live_app" || true
fi
if [[ -n "$live_fe" ]]; then
  echo "حذف volume کد فرانت: $live_fe"
  docker volume rm -f "$live_fe" || true
fi

if [[ -z "$live_app" || -z "$live_fe" ]]; then
  project="$(docker compose ls --format json 2>/dev/null | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(rows[0]["Name"] if rows else "")' 2>/dev/null || true)"
  if [[ -z "$project" ]]; then
    project="$(basename "$ROOT" | tr '[:upper:]' '[:lower:]')"
  fi
  docker volume rm -f "${project}_live_app" "${project}_live_frontend" 2>/dev/null || true
fi

echo "بالا آوردن سرویس‌ها با ایمیج جدید..."
docker compose up -d --build

echo "انتظار برای سلامت بک‌اند..."
ok=0
for i in $(seq 1 60); do
  if docker compose exec -T backend python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 2
done
if [[ "$ok" != "1" ]]; then
  echo "بک‌اند هنوز healthy نشد. لاگ:"
  docker compose logs --tail=80 backend
  exit 1
fi

echo -n "نسخه در حال اجرا: "
docker compose exec -T backend python3 -c "print(open('/app/VERSION',encoding='utf-8').read().strip())" 2>/dev/null || echo "(نامشخص)"
echo "اعمال سورس تمام شد. پنل zip برای این جهش لازم نیست."
