# راهنمای استقرار

## پیش‌نیاز

لینوکس، Docker Engine، Docker Compose v2، حداقل پیشنهادی شیت: ۲ vCPU / ۴GB RAM / ۱۰۰GB SSD (ظرفیت نهایی با کارفرما).

## مراحل

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
