# راهنمای استقرار

## پیش‌نیاز

لینوکس، Docker Engine، Docker Compose v2، حداقل پیشنهادی: ۲ vCPU / ۴GB RAM / ۱۰۰GB SSD (ظرفیت نهایی با کارفرما).

## پیکربندی نمونه

`.env.example` با `docker-compose.yml` هم‌خوان است و رمز/کلید قابل‌استفاده ندارد. `./scripts/bootstrap.sh` در صورت نبود `.env` آن را کپی می‌کند و مقدارهای `change-me-with-a-long-random-value` و `change-me-64-hex-chars` را با مقدار تصادفی عوض می‌کند.

در production این موارد اجباری‌اند و مقدار نمونه پذیرفته نمی‌شود:

- `SESSION_SECRET` (حداقل ۳۲ نویسه، غیرنمونه)
- `DATABASE_URL` / `POSTGRES_PASSWORD` (غیر از `eytan:eytan` و `change-me-*`)
- `BACKUP_ENCRYPTION_KEY` (۶۴ رقم hex منحصربه‌فرد)
- `SCAN_FAIL_CLOSED=true`
- `SMS_ENABLED=false` و `AUTOMATED_DELIVERY_ENABLED=false`

`UPDATE_PUBLIC_KEY` برای نصب بسته به‌روزرسانی لازم است؛ بدون آن بسته رد می‌شود.

بررسی پیکربندی Compose (داده موجود را پاک نمی‌کند):

```bash
docker compose --env-file .env.example config
```

## اعمال سورس (zip گیت‌هاب یا git pull)

کپی فایل‌های zip روی دیسک، برنامهٔ در حال اجرا را عوض نمی‌کند. کانتینرها کد را از volumeهای `live_app` و `live_frontend` می‌خوانند، نه مستقیم از پوشهٔ پروژه. پنل «به‌روزرسانی سامانه» هم روی همین نصب فعلی خراب است و جایگزین این مرحله نیست.

در **همان پوشه‌ای که بار اول `bootstrap.sh` اجرا شده** (فایل `.env` همان‌جا بماند):

```bash
# اگر zip گیت‌هاب را باز کرده‌اید، محتوای آن را روی همین پوشه بریزید؛ .env و infra/nginx/certs را نگه دارید.
chmod +x scripts/*.sh
./scripts/apply-source.sh
```

این اسکریپت فقط volume کد را عوض می‌کند. PostgreSQL، والت و فایل‌های کاربران پاک نمی‌شوند. `bootstrap.sh` را دوباره اجرا نکنید.

اگر روی **ویندوز / PowerShell** هستید (نه Git Bash)، `|| true` کار نمی‌کند. از این استفاده کنید:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\apply-source.ps1
```

یا `.\scripts\apply-source.cmd` اگر PowerShell اجرای `.ps1` را مسدود کرده باشد.

یا دستی:

```powershell
docker compose build backend frontend update-agent
docker compose stop backend frontend update-agent nginx
docker volume ls
docker volume rm -f <نام-volume-که-live_app-دارد>
docker volume rm -f <نام-volume-که-live_frontend-دارد>
docker compose up -d --build
```

## مراحل نصب نخست (محیط پاک)

این مسیر دادهٔ موجود را پاک نمی‌کند. `.env.example` حساب یا کلید قابل‌استفاده ندارد.

```bash
cp .env.example .env          # اگر .env وجود ندارد؛ bootstrap هم همین کار را می‌کند
./scripts/bootstrap.sh        # راز تصادفی، گواهی آزمایشی، docker compose up (بدون reset دیتابیس)
docker compose --env-file .env.example config
./scripts/healthcheck.sh      # /api/health
./scripts/create-admin.sh     # نخستین مدیر؛ بدون کاربر پیش‌فرض
```

سپس گواهی واقعی را جایگزین کنید و `PUBLIC_HOST` / `PUBLIC_ORIGIN` / `CORS_ORIGINS` را روی دامنه نهایی بگذارید.

Production با `change-me-*`، راز کوتاه، `SMS_ENABLED=true` یا `UPDATE_ALLOW_UNSIGNED=true` اجرا نمی‌شود.

بکاپ: `./scripts/backup.sh` — بازیابی: `docs/backup-recovery.md` و `./scripts/restore.sh`. مقصد خارجی اگر دیسک جدا ندارید خالی بماند (`BACKUP_EXTERNAL_PATH=`).

## تمدید TLS

مسیر گواهی از env خوانده می‌شود. تمدید با ابزار داخلی سازمان (نه ACME اجباری) و reload Nginx.

## آفلاین

`docker compose build` سپس `docker save` تمام imageها. روی سرور `docker load` و اجرای bootstrap. پایگاه ClamAV را جداگانه منتقل کنید.

## Health

- `/api/health` از Nginx یا loopback بک‌اند
- `/api/ready` برای پایگاه و ClamAV
- `./scripts/healthcheck.sh`

ارسال پیامک و گراف عمومی بخشی از health production نیستند و نباید فعال باشند.

## اسرار

فقط `.env` با مجوز ۶۰۰ یا Docker secrets. هیچ رمز پیش‌فرضی در production فعال نیست.

## پورت ۸۰ و تونل موقت

Nginx روی پورت ۸۰ خود سامانه را سرو می‌کند (ریدایرکت اجباری به HTTPS ندارد) تا تونل Cloudflare/ngrok به `http://127.0.0.1:80` وصل شود. HTTPS روی ۴۴۳ همچنان فعال است. کوکی نشست اگر درخواست از پشت HTTPS (از جمله تونل) بیاید Secure می‌شود.

نمایش موقت:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\share-internet.ps1
```

یا `.\scripts\share-internet.cmd`.

آدرس `trycloudflare.com` فقط تا وقتی اسکریپت باز است معتبر است.

