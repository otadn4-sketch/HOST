# راهنمای استقرار

## پیش‌نیاز

لینوکس، Docker Engine، Docker Compose v2، حداقل پیشنهادی شیت: ۲ vCPU / ۴GB RAM / ۱۰۰GB SSD (ظرفیت نهایی با کارفرما).

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
.\scripts\apply-source.ps1
```

یا دستی:

```powershell
docker compose build backend frontend update-agent
docker compose stop backend frontend update-agent nginx
docker volume ls
docker volume rm -f <نام-volume-که-live_app-دارد>
docker volume rm -f <نام-volume-که-live_frontend-دارد>
docker compose up -d --build
```

## مراحل نصب نخست

1. `git clone` یا انتقال bundle آفلاین
2. `./scripts/bootstrap.sh`
3. جایگزینی گواهی در `infra/nginx/certs` با گواهی دامنه واقعی
4. تنظیم `PUBLIC_HOST` و `PUBLIC_ORIGIN` و `CORS_ORIGINS` روی دامنه نهایی
5. `./scripts/create-admin.sh`
6. باز کردن فقط پورت‌های ۸۰/۴۴۳؛ پورت PostgreSQL و ClamAV نباید به شبکه عمومی publish شوند

## تمدید TLS

مسیر گواهی از env خوانده می‌شود. تمدید با ابزار داخلی سازمان (نه ACME اجباری) و reload Nginx.

## آفلاین

`docker compose build` سپس `docker save` تمام imageها. روی سرور `docker load` و اجرای bootstrap. پایگاه ClamAV را جداگانه منتقل کنید.

## Health

- `/api/health` از Nginx
- `/api/ready` برای پایگاه و ClamAV

## اسرار

فقط `.env` با مجوز ۶۰۰ یا Docker secrets. هیچ رمز پیش‌فرضی در production فعال نیست.
