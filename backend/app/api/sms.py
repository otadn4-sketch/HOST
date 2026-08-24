from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db, require_any_admin, require_system_admin
from app.config import get_settings
from app.models.entities import ExternalRecipient, FileObject, User
from app.schemas import SmsConfigPatchIn, SmsSendIn
from app.services.audit import write_audit
from app.services.policy import get_or_create_sms_settings
from app.services.sms import send_sms_message, serialize_sms_config

router = APIRouter(prefix="/api/sms", tags=["sms"])


def _effective_config(db: DBSession, *, reveal: bool = False) -> dict:
    settings = get_settings()
    row = get_or_create_sms_settings(db, settings)
    payload = serialize_sms_config(row, settings, reveal=reveal)
    if reveal:
        payload["api_key"] = row.api_key or settings.sms_api_key
    else:
        payload.pop("api_key", None)
    return payload


@router.get("/config")
def get_sms_config(db: DBSession = Depends(get_db), user: User = Depends(require_system_admin)):
    return {"config": _effective_config(db, reveal=False)}


@router.put("/config")
def update_sms_config(
    payload: SmsConfigPatchIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_system_admin),
):
    settings = get_settings()
    row = get_or_create_sms_settings(db, settings)
    if payload.enabled is not None:
        row.enabled = payload.enabled
    if payload.base_url is not None:
        row.base_url = payload.base_url.strip()
    if payload.api_key is not None and payload.api_key.strip() and "•" not in payload.api_key:
        row.api_key = payload.api_key.strip()
    if payload.sender is not None:
        row.sender = payload.sender.strip()
    if payload.http_method is not None:
        method = payload.http_method.strip().upper()
        if method not in {"GET", "POST", "PUT"}:
            raise HTTPException(status_code=400, detail="روش HTTP نامعتبر است.")
        row.http_method = method
    if payload.content_type is not None:
        ctype = payload.content_type.strip().lower()
        if ctype not in {"json", "form", "query"}:
            raise HTTPException(status_code=400, detail="نوع بدنه نامعتبر است.")
        row.content_type = ctype
    if payload.url_template is not None:
        row.url_template = payload.url_template.strip()
    if payload.body_template is not None:
        row.body_template = payload.body_template
    if payload.auth_header_name is not None:
        row.auth_header_name = payload.auth_header_name.strip()
    if payload.extra_headers is not None:
        row.extra_headers = payload.extra_headers
    write_audit(
        db,
        user=user,
        action="sms_config_updated",
        target_resource="تنظیمات پیامک",
        details="به‌روزرسانی پیکربندی ارائه‌دهنده پیامک",
        severity="warning",
        request=request,
    )
    return {"config": serialize_sms_config(row, settings, reveal=False)}


@router.get("/directory")
def sms_directory(db: DBSession = Depends(get_db), user: User = Depends(require_any_admin)):
    users = db.query(User).filter(User.status == "active").order_by(User.full_name.asc()).all()
    recipients = (
        db.query(ExternalRecipient)
        .filter(ExternalRecipient.is_active.is_(True))
        .order_by(ExternalRecipient.full_name.asc())
        .all()
    )
    return {
        "users": [
            {"id": u.id, "full_name": u.full_name, "phone": u.phone_number or ""}
            for u in users
            if (u.phone_number or "").strip()
        ],
        "recipients": [
            {"id": r.id, "full_name": r.full_name, "organization": r.organization, "phone": r.phone or ""}
            for r in recipients
            if (r.phone or "").strip()
        ],
    }


@router.post("/send")
def send_sms(
    payload: SmsSendIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_any_admin),
):
    message = (payload.message or "").strip()
    if len(message) < 1:
        raise HTTPException(status_code=400, detail="متن پیامک خالی است.")
    phones: list[str] = []
    seen: set[str] = set()

    def add_phone(raw: str | None) -> None:
        phone = (raw or "").strip()
        if phone and phone not in seen:
            seen.add(phone)
            phones.append(phone)

    for item in payload.phones or []:
        add_phone(item)
    if payload.user_ids:
        rows = db.query(User).filter(User.id.in_(payload.user_ids)).all()
        for row in rows:
            add_phone(row.phone_number)
    if payload.recipient_ids:
        rows = db.query(ExternalRecipient).filter(ExternalRecipient.id.in_(payload.recipient_ids)).all()
        for row in rows:
            add_phone(row.phone)
    if not phones:
        raise HTTPException(status_code=400, detail="هیچ شماره معتبری برای ارسال انتخاب نشده است.")

    file_title = ""
    if payload.file_id:
        file = db.query(FileObject).filter(FileObject.id == payload.file_id, FileObject.is_deleted.is_(False)).one_or_none()
        if file:
            file_title = file.title

    settings = get_settings()
    row = get_or_create_sms_settings(db, settings)
    config = serialize_sms_config(row, settings, reveal=True)
    config["api_key"] = row.api_key or settings.sms_api_key

    results = []
    success = 0
    for phone in phones:
        result = send_sms_message(config=config, to=phone, text=message)
        results.append({"to": phone, "ok": result["ok"], "error": result.get("error") or ""})
        write_audit(
            db,
            user=user,
            action="sms_sent" if result["ok"] else "sms_failed",
            target_resource=file_title or phone,
            target_type="sms",
            target_id=payload.file_id or phone,
            details=f"ارسال پیامک به {phone}" + (f" / {result.get('error')}" if not result["ok"] else ""),
            severity="info" if result["ok"] else "warning",
            request=request,
        )
        if result["ok"]:
            success += 1
    return {"sent": success, "failed": len(phones) - success, "results": results}
