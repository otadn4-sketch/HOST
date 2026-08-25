from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode

import httpx

from app.config import Settings, get_settings, sms_outbound_allowed
from app.models.entities import SmsSettings


PLACEHOLDERS = ("to", "text", "sender", "api_key")


def mask_secret(value: str) -> str:
    raw = value or ""
    if len(raw) <= 4:
        return "****" if raw else ""
    return "•" * 8 + raw[-4:]


def apply_template(template: str, mapping: dict[str, str]) -> str:
    out = template or ""
    for key, val in mapping.items():
        out = out.replace("{" + key + "}", val)
    return out


def serialize_sms_config(row: SmsSettings, settings: Settings | None = None, *, reveal: bool = False) -> dict[str, Any]:
    settings = settings or get_settings()
    api_key = row.api_key or settings.sms_api_key
    outbound = sms_outbound_allowed(settings)
    return {
        "enabled": False if not outbound else bool(row.enabled and settings.sms_enabled),
        "outbound_allowed": outbound,
        "feature_flag": bool(settings.sms_enabled) and outbound,
        "production_locked": settings.is_production,
        "note": (
            "ارسال پیامک و هر ارتباط خروجی تا تصمیم کتبی جدید در production غیرفعال است. "
            "ثبت دستی تحویل یک قابلیت جدا است و جایگزین پیامک نمی‌شود."
        ),
        "base_url": row.base_url or settings.sms_base_url,
        "api_key_set": bool(api_key),
        "api_key_masked": api_key if reveal else mask_secret(api_key),
        "sender": row.sender or settings.sms_sender,
        "http_method": (row.http_method or settings.sms_http_method or "POST").upper(),
        "content_type": (row.content_type or settings.sms_content_type or "json").lower(),
        "url_template": row.url_template or settings.sms_url_template,
        "body_template": row.body_template or settings.sms_body_template,
        "auth_header_name": row.auth_header_name or settings.sms_auth_header_name,
        "extra_headers": row.extra_headers or {},
        "timeout_seconds": settings.sms_timeout_seconds,
    }


def _http_send(method: str, url: str, headers: dict[str, str], body: str | None, timeout: float) -> tuple[int, str]:
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        response = client.request(method, url, headers=headers, content=body)
        return response.status_code, (response.text or "")[:800]


def send_sms_message(
    *,
    config: dict[str, Any],
    to: str,
    text: str,
) -> dict[str, Any]:
    if not sms_outbound_allowed():
        return {
            "ok": False,
            "error": "ارسال پیامک در این نسخه غیرفعال است و هیچ درخواست شبکه‌ای ارسال نشد.",
            "status_code": 0,
        }
    phone = (to or "").strip()
    message = (text or "").strip()
    if not phone or not message:
        return {"ok": False, "error": "شماره یا متن پیامک خالی است.", "status_code": 0}
    if not config.get("enabled"):
        return {"ok": False, "error": "ارسال پیامک در تنظیمات غیرفعال است.", "status_code": 0}
    mapping = {
        "to": phone,
        "text": message,
        "sender": str(config.get("sender") or ""),
        "api_key": str(config.get("api_key") or ""),
    }
    method = str(config.get("http_method") or "POST").upper()
    content_type = str(config.get("content_type") or "json").lower()
    url_template = str(config.get("url_template") or "").strip()
    base_url = str(config.get("base_url") or "").strip().rstrip("/")
    if url_template:
        url = apply_template(url_template, mapping)
    elif base_url:
        url = base_url
    else:
        return {"ok": False, "error": "آدرس API ارائه‌دهنده پیامک تنظیم نشده است.", "status_code": 0}

    headers = {"Accept": "application/json"}
    extra = config.get("extra_headers") or {}
    if isinstance(extra, dict):
        for key, val in extra.items():
            headers[str(key)] = apply_template(str(val), mapping)
    auth_header = str(config.get("auth_header_name") or "").strip()
    if auth_header and mapping["api_key"]:
        if auth_header.lower() == "authorization" and not mapping["api_key"].lower().startswith("bearer "):
            headers[auth_header] = f"Bearer {mapping['api_key']}"
        else:
            headers[auth_header] = mapping["api_key"]

    body = None
    if method == "GET":
        if "{" not in (url_template or "") and content_type in {"query", "form", "json"}:
            query = urlencode({"receptor": phone, "to": phone, "sender": mapping["sender"], "message": message, "text": message}, doseq=True)
            url = f"{url}{'&' if '?' in url else '?'}{query}"
    else:
        template = str(config.get("body_template") or "").strip()
        if not template:
            if content_type == "form":
                template = "receptor={to}&sender={sender}&message={text}"
            else:
                template = '{"receptor":"{to}","sender":"{sender}","message":"{text}"}'
        body = apply_template(template, mapping)
        if content_type == "form":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            headers["Content-Type"] = "application/json; charset=utf-8"

    timeout = float(config.get("timeout_seconds") or 15)
    try:
        status, raw = _http_send(method, url, headers, body, timeout)
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"ارتباط با ارائه‌دهنده پیامک برقرار نشد: {exc}", "status_code": 0}
    ok = 200 <= status < 300
    return {
        "ok": ok,
        "status_code": status,
        "error": "" if ok else (raw or f"کد پاسخ {status}"),
        "provider_response": raw if ok else "",
        "to": phone,
    }
