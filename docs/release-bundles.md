# ساخت بسته به‌روزرسانی امضاشده

کلید خصوصی هرگز روی سرور قرار نمی‌گیرد.

```bash
python tools/generate_signing_keys.py --out-dir ./release-keys
# UPDATE_PUBLIC_KEY را در .env سرور با محتوای ed25519.pub بگذارید

npm --prefix frontend run build
python tools/build_release.py --version 1.0.1 --secret-key ./release-keys/ed25519.secret \
  --changelog "رفع‌ها" --out dist/eytan-1.0.1.zip
```

بسته فقط شامل frontend استاتیک، کد backend/app، نسخه‌های alembic، VERSION و CHANGELOG است. وجود `install.sh` یا `docker-compose.yml` باعث رد شدن می‌شود.

نصب: تنظیمات ← به‌روزرسانی سامانه ← بارگذاری ← تأیید نهایی مدیر.
