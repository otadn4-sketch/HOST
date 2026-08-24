from __future__ import annotations

from fastapi import HTTPException, Request

from app.config import Settings, get_settings

PHASE_CATALOG = [
    {
        "id": 1,
        "code": "archive",
        "title": "بایگانی و ثبت دستی",
        "summary": "مخزن فایل، ثبت دستی تحویل، جست‌وجو و پالایش تراکنش‌ها.",
        "flag": "phase_1_archive_enabled",
    },
    {
        "id": 2,
        "code": "meetings",
        "title": "ثبت جلسات و ارائه‌ها",
        "summary": "ثبت تعاملات حضوری و ارائه‌های بیرونی به‌صورت تراکنش تعامل.",
        "flag": "phase_2_meetings_enabled",
    },
    {
        "id": 3,
        "code": "recipients",
        "title": "پروفایل مخاطبان بیرونی",
        "summary": "تاریخچه تعامل، منشأ درخواست و گزارش‌های تحویل‌شده.",
        "flag": "phase_3_recipient_profiles_enabled",
    },
    {
        "id": 4,
        "code": "sharing",
        "title": "اشتراک‌گذاری و کنترل دسترسی دانه‌ای",
        "summary": "پیوند امن و RBAC داخلی/خارجی. تا فعال‌سازی پرچم خاموش است.",
        "flag": "phase_4_sharing_enabled",
    },
    {
        "id": 5,
        "code": "security_graph",
        "title": "امنیت، پالایش سند و گراف محلی",
        "summary": "آمادگی آزمون نفوذ، پالایش PDF/Word، گراف تعاملات فقط روی localhost.",
        "flag": "phase_5_security_graph_enabled",
    },
]


def phase_status(settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    phases = []
    for item in PHASE_CATALOG:
        enabled = bool(getattr(settings, item["flag"], False))
        phases.append({**item, "enabled": enabled})
    return {
        "product_mode": "manual_logging_archive",
        "automated_delivery_enabled": False,
        "automated_delivery_deprecated": True,
        "automated_delivery_note": (
            "ارسال خودکار لینک یا فایل از طریق پیام‌رسان و پیامک منسوخ و غیرفعال است. "
            "تحویل فقط به‌صورت ثبت دستی انجام می‌شود."
        ),
        "phases": phases,
        "faran": {
            "enabled": bool(settings.faran_enabled),
            "configured": bool((settings.faran_base_url or "").strip()),
            "allow_network": bool(settings.faran_allow_network),
            "mode": "stub",
        },
    }


def require_phase(flag_name: str, message: str) -> None:
    settings = get_settings()
    if not bool(getattr(settings, flag_name, False)):
        raise HTTPException(status_code=403, detail=message)


def is_loopback_request(request: Request) -> bool:
    host = (request.headers.get("host") or "").split(":")[0].lower()
    if host not in {"localhost", "127.0.0.1", "::1"}:
        return False
    forwarded = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip().split(":")[0].lower()
    if forwarded and forwarded not in {"localhost", "127.0.0.1", "::1"}:
        return False
    return True


require_phase = require_phase
phase_status = phase_status
is_loopback_request = is_loopback_request
