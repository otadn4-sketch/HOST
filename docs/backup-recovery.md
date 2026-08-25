# پشتیبان‌گیری و بازیابی

بکاپ دیتابیس و فایل‌های vault **جدا** و با AES-256-GCM رمز می‌شوند. مسیر `BACKUP_PATH` باید بیرون از vault و quarantine باشد.

## چه چیزی ذخیره می‌شود

- `eytan-db-<timestamp>.bin` : dump پایگاه (sqlite file bytes یا `pg_dump`)
- `eytan-vault-<timestamp>.bin` : tar رمزنگاری‌شدهٔ vault
- قرنطینه موقت و `.env` داخل این آرشیوها نیستند

کلید: `BACKUP_ENCRYPTION_KEY` فقط ۶۴ رقم hex منحصربه‌فرد، جدا از رمز دیتابیس. مقدار نمونه یا ضعیف در production رد می‌شود و در مخزن ثبت نمی‌شود.

مقصد خارجی اختیاری: `BACKUP_EXTERNAL_PATH`. اگر خالی یا ناموجود باشد، فقط کپی محلی در `BACKUP_PATH` نوشته می‌شود.

## تهیه بکاپ

```bash
./scripts/backup.sh
# یا
PYTHONPATH=backend python3 -m app.cli backup --note "daily"
```

دادهٔ زنده حذف یا reset نمی‌شود.

## بازیابی کنترل‌شده

بازیابی پیش‌فرض به vault زنده نمی‌نویسد:

```bash
DB_ARCHIVE=/var/lib/eytan/backups/eytan-db-....bin \
VAULT_ARCHIVE=/var/lib/eytan/backups/eytan-vault-....bin \
DEST_VAULT=/tmp/eytan-restore-vault \
DEST_DB=/tmp/eytan-restore.dump \
./scripts/restore.sh
```

بارگذاری dump در PostgreSQL فقط روی یک پایگاه **جدا** و با دستور صریح انجام شود:

```bash
pg_restore --clean --if-exists -U eytan -d eytan_restore < /tmp/eytan-restore.dump
```

آزمون بازیابی: یک دادهٔ نمونه را backup و restore کنید و SHA-256 فایل را مقایسه کنید. این کار روی دادهٔ production اجرا نشود.

## تناوب پیشنهادی

روزانه پایگاه و vault، نگهداری روی دیسک جدا. آزمون بازیابی دوره‌ای.
