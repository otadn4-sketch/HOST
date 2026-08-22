# به‌روزرسانی سامانه از طریق zip

از پنل **تنظیمات ← به‌روزرسانی سامانه** فایل zip پروژه را بارگذاری کنید، سپس **تأیید نهایی و نصب** را بزنید.

نصب را خود سامانه انجام می‌دهد (نه اجرای `install.sh` / `docker-compose`). اگر نصب ناموفق باشد، متن خطا نمایش داده می‌شود و می‌توانید دوباره تلاش کنید.

- کد `backend/app` روی سرویس backend اعمال می‌شود و پس از چند ثانیه فرآیند تازه می‌شود.
- رابط کاربری فقط وقتی عوض می‌شود که داخل zip پوشهٔ `frontend/dist` (خروجی `npm run build`) باشد.
- `docker-compose.yml` و `install.sh` اجرا نمی‌شوند.

## اگر دکمه نصب هنوز روی سرور فعلی خطا می‌دهد

کد نصب قبلی به `update-agent` وابسته بود و با توکن خالی یا ری‌استارت حین نصب، وضعیت بسته از `validated` خارج می‌شد. برای رسیدن به این نسخهٔ نصب‌کننده یک‌بار روی سرور:

```bash
git pull
docker compose up -d --build
```

بعد از آن، به‌روزرسانی‌های بعدی از همان پنل zip قابل نصب است.

## بستهٔ امضاشده (اختیاری)

```bash
python tools/generate_signing_keys.py --out-dir ./release-keys
npm --prefix frontend run build
python tools/build_release.py --version 1.2.1 --secret-key ./release-keys/ed25519.secret \
  --changelog "نسخه ۱.۲.۱" --out dist/eytan-1.2.1.zip
```
