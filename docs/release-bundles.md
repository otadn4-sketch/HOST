# به‌روزرسانی سامانه از طریق zip

## روش توصیه‌شده برای مدیر سامانه

از پنل **تنظیمات ← به‌روزرسانی سامانه** همان فایل zip پروژه را بارگذاری کنید (حتی اگر پوشهٔ تو در تو باشد و `manifest.json` نداشته باشد). سپس روی **تأیید نهایی و نصب** بزنید.

- `docker-compose.yml` و `install.sh` اجرا نمی‌شوند و از بسته حذف می‌شوند.
- کد `backend/app` روی سرویس backend اعمال می‌شود.
- رابط کاربری فقط وقتی عوض می‌شود که داخل zip پوشهٔ `frontend/dist` (خروجی `npm run build`) یا بستهٔ ساخته‌شده با `tools/build_release.py` باشد.

## بستهٔ امضاشده (اختیاری)

```bash
python tools/generate_signing_keys.py --out-dir ./release-keys
npm --prefix frontend run build
python tools/build_release.py --version 1.1.0 --secret-key ./release-keys/ed25519.secret \
  --changelog "نسخه ۱.۱.۰" --out dist/eytan-1.1.0.zip
```

اگر `UPDATE_PUBLIC_KEY` در `.env` خالی باشد، zip منبع هم پذیرفته می‌شود. اگر کلید عمومی تنظیم شده باشد و بسته امضا داشته باشد، امضا بررسی می‌شود.
