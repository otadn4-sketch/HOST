# سامانه اشتراک‌گذاری فایل شبکه کانون‌های تفکر ایران «ایتان»

نسخه ۱.۲.۱: نصب به‌روزرسانی zip توسط خود سامانه (با امکان تلاش دوباره و نمایش خطا). پیش‌نمایش محتوا، تفکیک بازدید داشبورد، و پالت کرم / قهوه‌ای سوخته.

نسخهٔ قابل‌استقرار و خودمیزبان برای شبکه کانون‌های تفکر ایران «ایتان». رابط فارسی/RTL حفظ شده و به API واقعی FastAPI متصل است. هیچ سرویس ابری جانبی، Firebase، S3 یا telemetry بیرونی استفاده نمی‌شود. هوش مصنوعی به‌صورت پیش‌فرض با دستیار محلی و دو پرامپت سازمانی کار می‌کند.

## راه‌اندازی سریع (آنلاین)

روی سرور لینوکس با Docker و Docker Compose:

```bash
cp .env.example .env          # در صورت نیاز؛ bootstrap هم می‌سازد
./scripts/bootstrap.sh        # ساخت اسرار، گواهی آزمایشی، بالا آوردن سرویس‌ها
./scripts/create-admin.sh     # ایجاد نخستین مدیر سامانه (بدون کاربر پیش‌فرض)
```

سامانه روی `https://<PUBLIC_HOST>` در دسترس است. گواهی خودامضا فقط برای آزمایش است؛ برای تولید، مسیر `TLS_CERT_PATH` / `TLS_KEY_PATH` را به گواهی واقعی تغییر دهید.

## راه‌اندازی آفلاین

1. روی ماشینی با اینترنت: `docker compose build` سپس `docker save` برای imageهای `postgres:16-alpine`، `nginx:1.27-alpine`، `clamav/clamav:1.4` و imageهای buildشدهٔ frontend/backend/update-agent.
2. انتقال فایل‌های `*.tar`، سورس، و `.env` به سرور ایزوله.
3. `docker load -i ...` و سپس `./scripts/bootstrap.sh`.
4. پایگاه امضای ClamAV را نیز به‌صورت فایل `clamav_db` منتقل کنید؛ بدون آن پویش fail-closed فایل‌ها را قرنطینه می‌کند.

جزئیات: `docs/deployment-guide.md`.

## پیش‌فرض‌های امن

- Production هیچ کاربر یا رمز پیش‌فرضی ندارد.
- `EYTAN_SEED_DEV` فقط برای محیط توسعه و در صورت تنظیم رمزها در `.env`.
- اسرار فقط در `.env` یا Docker secrets.

## ساختار

| مسیر | نقش |
| --- | --- |
| `frontend/` | React / Vite / RTL |
| `backend/` | FastAPI + RBAC + بارگذاری قرنطینه‌ای |
| `infra/` | Nginx TLS و ClamAV |
| `update-agent/` | نصب بسته امضاشده |
| `tests/` | واحد، یکپارچه، پذیرش AC-01 تا AC-09 |
| `docs/` | نیازمندی، معماری، استقرار، بکاپ، مدیر، مدل تهدید |
| `sheet_data/` | کپی محلی شیت؛ شیت گوگل تغییر داده نمی‌شود |

## آزمون

```bash
pip install -r backend/requirements-dev.txt
pytest
```
