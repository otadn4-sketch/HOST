from __future__ import annotations

from fastapi import HTTPException, Request

from app.config import Settings, get_settings, sms_outbound_allowed

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
        "summary": "پیوند امن و RBAC داخلی/خارجی. تا تصمیم کتبی خاموش است.",
        "flag": "phase_4_sharing_enabled",
    },
    {
        "id": 5,
        "code": "security_graph",
        "title": "امنیت، پالایش سند و گراف محلی",
        "summary": "پالایش سند با fail-safe؛ گراف تعاملات فقط روی localhost و خارج از وب عمومی.",
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
        "sms_enabled": False if settings.is_production else bool(settings.sms_enabled),
        "sms_outbound_allowed": sms_outbound_allowed(settings),
        "graph_localhost_only": True,
        "graph_production_disabled": settings.is_production,
        "automated_delivery_note": (
            "ارسال خودکار لینک یا فایل از طریق پیام‌رسان و پیامک منسوخ است و در production "
            "تا تصمیم کتبی جدید غیرفعال می‌ماند. سامانه فقط ثبت دستی می‌کند: فایل، مخاطب، تاریخ، هدف، کانال، یادداشت."
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
    """Local-only graph access. Production never returns graph data.

    Peer address is required. X-Forwarded-* cannot make a remote client look local.
    """
    settings = get_settings()
    if settings.is_production:
        return False
    peer = ""
    if request.client and request.client.host:
        peer = request.client.host.strip().strip("[]").split("%")[0].lower()
    loopback_peers = {"127.0.0.1", "::1", "localhost", "testclient"}
    if peer not in loopback_peers:
        return False
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip().split(":")[0].lower()
    forwarded_for = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip().split(":")[0].lower()
    if forwarded_host and forwarded_host not in {"localhost", "127.0.0.1", "::1", "testserver"}:
        return False
    if forwarded_for and forwarded_for not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        return False
    return True


require_phase = require_phase
phase_status = phase_status
is_loopback_request = is_loopback_request
