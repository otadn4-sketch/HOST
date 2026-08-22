# به‌روزرسانی سامانه از طریق zip

از پنل **تنظیمات ← به‌روزرسانی سامانه** فایل zip پروژه را بارگذاری کنید، سپس **تأیید نهایی و نصب** را بزنید.

- کد `backend/app` روی سرویس backend اعمال می‌شود.
- رابط کاربری از zip فقط با وجود `frontend/dist` عوض می‌شود؛ در استقرار با Docker، رابط از ایمیج frontend هم به‌روز می‌شود.
- `docker-compose.yml` و `install.sh` اجرا نمی‌شوند.

## پیام «نصب ناموفق بود و rollback انجام شد»

این پیام از نصب‌کنندهٔ قدیمی است. volume به نام `live_app` روی `/app` سوار است و اگر یک‌بار پر شده باشد، `docker compose build` به‌تنهایی کد داخل volume را عوض نمی‌کند. از نسخهٔ ۱.۲.۲ به بعد، هنگام بالا آمدن کانتینر اگر ایمیج جدیدتر باشد همان volume تازه می‌شود:

```bash
git pull
docker compose up -d --build
```

نیازی به پاک کردن دیتابیس یا فایل‌های والت نیست. بعد از بالا آمدن، نسخه در پنل به‌روزرسانی باید ۱.۲.۲ باشد. از آن به بعد zipهای بعدی از خود پنل نصب می‌شوند.

## بستهٔ امضاشده (اختیاری)

```bash
python tools/generate_signing_keys.py --out-dir ./release-keys
npm --prefix frontend run build
python tools/build_release.py --version 1.2.2 --secret-key ./release-keys/ed25519.secret \
  --changelog "نسخه ۱.۲.۲" --out dist/eytan-1.2.2.zip
```
