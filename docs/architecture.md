# معماری

```
[مرورگر RTL] --HTTPS--> [Nginx TLS] --/--> [frontend nginx]
                                 --/api--> [FastAPI]
                                              |-- PostgreSQL
                                              |-- volume vault (خارج از web root)
                                              |-- volume quarantine
                                              |-- ClamAV TCP 3310
[مدیر سامانه] --بسته امضاشده--> FastAPI staging --> [update-agent]
```

## داده

جداول عملیاتی: users, groups, sessions, files, file_permissions, audit_logs (append-only), security_policies, recovery_tokens, system_updates, maintenance_state.

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

## به‌روزرسانی

بسته باید `manifest.json` با SHA-256 همه فایل‌ها و امضای Ed25519 داشته باشد. کلید خصوصی آفلاین است. update-agent فایل‌های `install.sh` و `docker-compose.yml` را رد می‌کند و کد دلخواه داخل ZIP را اجرا نمی‌کند.

## هوش مصنوعی

حذف شده. در صورت نیاز آینده فقط ماژول اختیاری مدل محلی با پیش‌فرض غیرفعال.
