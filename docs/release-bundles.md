# به‌روزرسانی کد روی نصب موجود

پنل zip داخل سامانه فقط بستهٔ دارای manifest، فهرست hash و امضای Ed25519 با `UPDATE_PUBLIC_KEY` را می‌پذیرد. بسته بدون امضا در production رد می‌شود.

## روش درست: zip گیت‌هاب یا git pull

1. در **همان پوشه‌ای که بار اول سامانه را بالا آورده‌اید** کار کنید (فایل `.env` آنجاست).
2. محتوای zip گیت‌هاب را روی همان پوشه کپی کنید؛ `.env` و `infra/nginx/certs` را بازنویسی نکنید.
3. اجرا:

```bash
chmod +x scripts/*.sh
./scripts/apply-source.sh
```

این اسکریپت ایمیج را از سورس همین پوشه می‌سازد، فقط volumeهای `live_app` و `live_frontend` را عوض می‌کند و سرویس را بالا می‌آورد. دیتابیس، والت و فایل‌های کاربران پاک نمی‌شوند.

روی ویندوز / PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\apply-source.ps1
```

یا volumeها را با `docker volume ls` پیدا کنید و `docker volume rm -f` بزنید؛ `|| true` مال لینوکس است و در PowerShell خطا می‌دهد.


پس از موفقیت، نسخه در خروجی اسکریپت و در پنل به‌روزرسانی باید با `VERSION` سورس یکی باشد.
