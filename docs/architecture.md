# معماری

```
[مرورگر RTL] --HTTPS--> [Nginx TLS] --/--> [frontend nginx]
                                 --/api--> [FastAPI]
                                              |-- PostgreSQL
                                              |-- volume vault (خارج از web root)
                                              |-- volume quarantine
                                              |-- ClamAV TCP 3310
[مدیر سامانه] --بسته امضاشده--> FastAPI staging --> نصب مستقیم / update-agent
```

## داده

جداول عملیاتی: users, groups, sessions, files, file_permissions, audit_logs (append-only), security_policies, recovery_tokens, system_updates, maintenance_state, external_recipients, interaction_transactions, meeting_logs, share_links, document_scrub_jobs, faran_sync_records.

ارسال خودکار لینک/فایل از طریق پیام‌رسان یا پیامک در production وجود ندارد و تا تصمیم کتبی جدید نباید فعال شود. تحویل با ثبت دستی تراکنش انجام می‌شود. اشتراک فاز ۴ فقط درون‌شبکه و بدون پیوند عمومی است. گراف تعاملات در production داده برنمی‌گرداند.

مسیر فیزیکی فایل هرگز در JSON پاسخ نمی‌آید؛ فقط شناسه تصادفی `stored_vault_name`.

## امنیت

- گذرواژه Argon2id
- نشست در دیتابیس، کوکی HttpOnly / SameSite=Lax / Secure در production
- CSRF برای متدهای تغییردهنده
- Rate limit ورود و بازیابی
- قفل موقت حساب
- RBAC در سرور
- بارگذاری streaming به قرنطینه، SHA-256، magic bytes، allowlist، سپس ClamAV، سپس انتقال اتمی به vault در صورت پاک بودن
- Fail-closed اگر ClamAV در دسترس نباشد (`SCAN_FAIL_CLOSED`)
- SMS با `sms_outbound_allowed`؛ در production همیشه False

## به‌روزرسانی

بسته باید `manifest.json` با SHA-256 همه فایل‌ها و امضای Ed25519 داشته باشد. کلید عمومی از `UPDATE_PUBLIC_KEY`. کلید خصوصی آفلاین است. بسته بدون manifest، hash یا امضا در production رد می‌شود. `install.sh` و `docker-compose.yml` داخل ZIP اجرا نمی‌شوند.

## هوش مصنوعی

گفت‌وگوی آزاد حذف شده (410). خلاصه‌سازی فایل در صورت پیکربندی باقی است.
