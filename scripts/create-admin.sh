#!/usr/bin/env bash
# Interactive first-admin creation. Do not put username or password in this file.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "این فایل را ویرایش نکنید. جواب‌ها را در ترمینال بنویسید."
echo "نام کاربری لاتین است (مثلاً admin)."
echo "گذرواژه را اینجا تایپ نکنید؛ بعد از ایمیل، پشت prompt مربوط به password وارد کنید."
echo "گذرواژه حداقل ۱۲ نویسه، با حرف بزرگ، حرف کوچک، رقم و نویسه ویژه است."
echo

read -r -p "username: " USERNAME
read -r -p "full name: " FULL_NAME
read -r -p "email: " EMAIL
read -r -s -p "password: " PASSWORD
echo
read -r -s -p "password again: " PASSWORD2
echo

USERNAME="${USERNAME#"${USERNAME%%[![:space:]]*}"}"
USERNAME="${USERNAME%"${USERNAME##*[![:space:]]}"}"
FULL_NAME="${FULL_NAME#"${FULL_NAME%%[![:space:]]*}"}"
FULL_NAME="${FULL_NAME%"${FULL_NAME##*[![:space:]]}"}"
EMAIL="${EMAIL#"${EMAIL%%[![:space:]]*}"}"
EMAIL="${EMAIL%"${EMAIL##*[![:space:]]}"}"

if [[ -z "$USERNAME" || -z "$FULL_NAME" || -z "$EMAIL" || -z "$PASSWORD" ]]; then
  echo "نام کاربری، نام کامل، ایمیل و گذرواژه لازم است."
  unset PASSWORD PASSWORD2
  exit 1
fi
if [[ "$PASSWORD" != "$PASSWORD2" ]]; then
  echo "گذرواژه‌ها یکسان نیستند."
  unset PASSWORD PASSWORD2
  exit 1
fi

docker compose exec -T backend python -m app.cli create-admin \
  --username "$USERNAME" --full-name "$FULL_NAME" --email "$EMAIL" --password "$PASSWORD"
unset PASSWORD PASSWORD2
