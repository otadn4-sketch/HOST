#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "نام کاربری لاتین است (مثلاً admin). گذرواژه حداقل ۱۲ نویسه، با حرف بزرگ، حرف کوچک، رقم و نویسه ویژه."
read -r -p "username: " USERNAME
read -r -p "full name: " FULL_NAME
read -r -p "email: " EMAIL
docker compose exec -T backend python -m app.cli create-admin \
  --username "$USERNAME" --full-name "$FULL_NAME" --email "$EMAIL"
