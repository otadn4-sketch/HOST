# سامانه بایگانی و ثبت تعامل شبکه کانون‌های تفکر ایران «ایتان»

نسخه ۱.۵.۰: آرشیو فایل و ثبت دستی ارتباطات. ارسال سنتی در پیام‌رسان‌ها خارج از سامانه انجام می‌شود؛ سامانه فقط ثبت می‌کند چه فایلی، به چه مخاطبی، در چه تاریخی، با چه هدفی، از چه کانالی و با چه یادداشتی.

ارسال خودکار، ارسال پیامک و هرگونه ارتباط خروجی در production غیرفعال است مگر اینکه تصمیم کتبی جدیدی ثبت شود.

نسخهٔ قابل‌استقرار و خودمیزبان. رابط فارسی/RTL به API واقعی FastAPI متصل است. هیچ سرویس ابری جانبی، Firebase، S3 یا telemetry بیرونی استفاده نمی‌شود.

## راه‌اندازی سریع (آنلاین)

روی سرور لینوکس با Docker و Docker Compose:

```bash
cp .env.example .env          # در صورت نیاز؛ bootstrap هم می‌سازد
./scripts/bootstrap.sh        # ساخت اسرار، گواهی آزمایشی، بالا آوردن سرویس‌ها
./scripts/create-admin.sh     # ایجاد نخستین مدیر سامانه (بدون کاربر پیش‌فرض)
./scripts/healthcheck.sh      # بررسی سلامت HTTPS یا loopback بک‌اند
```

سامانه روی `https://<PUBLIC_HOST>` در دسترس است. گواهی خودامضا فقط برای آزمایش است؛ برای تولید، مسیر `TLS_CERT_PATH` / `TLS_KEY_PATH` را به گواهی واقعی تغییر دهید.

`.env.example` رمز، کلید API یا حساب آماده ندارد. مقدارهای `change-me-*` را قبل از production عوض کنید؛ در غیر این صورت فرآیند راه‌اندازی production متوقف می‌شود.

## راه‌اندازی آفلاین

1. روی ماشینی با اینترنت: `docker compose build` سپس `docker save` برای imageهای `postgres:16-alpine`، `nginx:1.27-alpine`، `clamav/clamav:1.4` و imageهای buildشدهٔ frontend/backend/update-agent.
2. انتقال فایل‌های `*.tar`، سورس، و `.env` به سرور ایزوله.
3. `docker load -i ...` و سپس `./scripts/bootstrap.sh`.
4. پایگاه امضای ClamAV را نیز به‌صورت فایل `clamav_db` منتقل کنید؛ بدون آن پویش fail-closed فایل‌ها را قرنطینه می‌کند و امن تلقی نمی‌کند.

جزئیات: `docs/deployment-guide.md`.

## پیش‌فرض‌های امن

- Production هیچ کاربر یا رمز پیش‌فرضی ندارد.
- `SMS_ENABLED=false` و `AUTOMATED_DELIVERY_ENABLED=false`.
- به‌روزرسانی فقط بستهٔ دارای manifest، hash list و امضای Ed25519 با `UPDATE_PUBLIC_KEY`.
- گراف تعاملات فقط localhost.
- `EYTAN_SEED_DEV` فقط برای محیط توسعه و در صورت تنظیم رمزها در `.env`.
- اسرار فقط در `.env` یا Docker secrets.

## ساختار

| مسیر | نقش |
| --- | --- |
| `frontend/` | React / Vite / RTL |
| `backend/` | FastAPI + RBAC + بارگذاری قرنطینه‌ای |
| `infra/` | Nginx TLS و ClamAV |
| `update-agent/` | نصب بسته امضاشده |
| `tests/` | واحد، یکپارچه، پذیرش AC-01 تا AC-13 |
| `docs/` | نیازمندی، معماری، استقرار، بکاپ، مدیر، مدل تهدید |

## آزمون

در محیط ایزولهٔ پروژه (نه نصب سراسری):

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-dev.txt
PYTHONPATH=backend python3 -m pytest tests -q
```

## پیش‌نمایش فایل‌های آفیس

فایل‌های `.docx` / `.xlsx` / `.pptx` بسته ZIP هستند. پیش‌نمایش متن استخراج‌شده را نشان می‌دهد، نه بایت خام `PK`.

## نمایش موقت روی اینترنت (ویندوز)

سامانه روی همین ماشین با Docker اجرا می‌شود. برای نشان‌دادن موقت به دیگران، بعد از بالا بودن استک:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\apply-source.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\share-internet.ps1
```

اگر خطای ExecutionPolicy آمد، همان دستور Bypass را بزنید یا `.\scripts\apply-source.cmd` و `.\scripts\share-internet.cmd`.

اسکریپت یک آدرس `https://....trycloudflare.com` چاپ می‌کند. با Ctrl+C تونل بسته می‌شود. این کار سامانه را موقتاً روی اینترنت قرار می‌دهد؛ پس از نمایش، اسکریپت را متوقف کنید.

روی لینوکس: `./scripts/share-internet.sh`

## وب‌اپ موبایل

روی گوشی، سامانه را در مرورگر باز کنید. بنر «نصب نسخه اپلیکیشن» یا منوی مرورگر (Add to Home Screen / نصب برنامه) آن را مثل اپ روی صفحه اصلی می‌گذارد و در حالت standalone باز می‌شود.
