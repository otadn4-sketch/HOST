from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db
from app.config import Settings, get_settings
from app.models.entities import FileObject, User
from app.schemas import AiChatIn, AiSummarizeIn
from app.security.rbac import evaluate_file_access
from app.services.audit import write_audit
from app.services.files import get_visible_file, vault_abs
from app.services.policy import get_or_create_ai_settings

router = APIRouter(prefix="/api/ai", tags=["ai"])

TEXT_EXTENSIONS = {"txt", "csv", "md", "json", "xml", "log", "html", "htm"}
MAX_EXCERPT = 12_000


def _excerpt_from_file(settings: Settings, file: FileObject) -> str:
    if file.scan_status != "clean":
        return ""
    try:
        path = vault_abs(settings, file.storage_relpath)
    except Exception:
        return ""
    if not path.is_file():
        return ""
    ext = (file.extension or "").lower().lstrip(".")
    try:
        raw = path.read_bytes()[: MAX_EXCERPT * 2]
    except OSError:
        return ""
    if ext in TEXT_EXTENSIONS:
        return raw.decode("utf-8", errors="ignore")[:MAX_EXCERPT]
    if ext == "pdf":
        text = raw.decode("latin-1", errors="ignore")
        pieces = []
        for part in text.split("(")[1:]:
            chunk = part.split(")", 1)[0]
            if chunk.isprintable() and len(chunk) > 4:
                pieces.append(chunk)
            if sum(len(p) for p in pieces) > MAX_EXCERPT:
                break
        return " ".join(pieces)[:MAX_EXCERPT]
    return ""


def _visible_files(db: DBSession, user: User, file_ids: list[str] | None) -> list[FileObject]:
    rows = (
        db.query(FileObject)
        .filter(FileObject.is_deleted.is_(False), FileObject.is_current_version.is_(True))
        .order_by(FileObject.created_at.desc())
        .all()
    )
    wanted = set(file_ids or [])
    result = []
    for file in rows:
        if wanted and file.id not in wanted:
            continue
        if not evaluate_file_access(user, file, file.permissions).can_view:
            continue
        result.append(file)
        if len(result) >= 40:
            break
    return result


def _file_card(file: FileObject, excerpt: str, admin: bool) -> str:
    lines = [
        f"- عنوان: {file.title}",
        f"- نام فایل: {file.original_name}",
        f"- موضوع: {file.topic or '—'}",
        f"- رده محرمانگی: {file.classification}",
        f"- توضیح: {file.description or '—'}",
        f"- برچسب‌ها: {', '.join(file.tags or []) or '—'}",
    ]
    if excerpt:
        lines.append(f"- گزیده متن: {excerpt[:2500]}")
    if admin:
        lines.append(f"- شناسه داخلی: {file.id}")
    return "\n".join(lines)


def _local_chat_reply(message: str, files: list[FileObject]) -> str:
    titles = "، ".join(f.title for f in files[:8]) or "هیچ منبع انتخاب‌شده‌ای"
    hits = [
        f
        for f in files
        if any(
            token in " ".join([(f.title or ""), (f.topic or ""), (f.description or "")]).lower()
            for token in message.lower().split()
            if len(token) > 2
        )
    ]
    cited = hits[:4] or files[:3]
    bullets = []
    for f in cited:
        bullets.append(
            f"- **{f.title}** ({f.topic or 'بدون موضوع'}): {f.description or 'شرح تکمیلی در مخزن ثبت نشده است.'}"
        )
    return (
        f"بر اساس منابع در دسترس ({titles}):\n\n"
        f"**پاسخ به پرسش «{message.strip()}»:**\n\n"
        + "\n".join(bullets)
        + "\n\nاگر نیاز به جزئیات دقیق‌تری از یک سند خاص دارید، عنوان آن را مشخص کنید."
    )


def _local_summary(file: FileObject, excerpt: str, mode: str) -> str:
    mode_label = "فنی و زیرساختی" if mode == "technical" else "جامع و مدیریتی"
    excerpt_block = excerpt[:1800] if excerpt else (file.description or "متن استخراج‌شده‌ای از این قالب در دسترس نیست؛ خلاصه بر اساس فراداده سند تهیه شده است.")
    return f"""### 📌 چکیده اجرایی
سند **«{file.title}»** در موضوع **«{file.topic or 'اسناد سازمانی'}»** با رده محرمانگی **«{file.classification}»** ثبت شده است. خلاصه زیر به صورت {mode_label} تهیه شده است.

### 🔍 محورها و یافته‌های کلیدی
- واحد/موضوع: {file.topic or 'ثبت‌نشده'}
- قالب و نسخه: {file.extension.upper()} • {file.version}
- شرح موجود: {file.description or '—'}
- گزیده محتوا: {excerpt_block}

### 🛡️ ملاحظات امنیتی و دسترسی
- دسترسی مطابق ماتریس نقش‌محور و مجوزهای فایل اعمال می‌شود.
- هر مشاهده یا دریافت در رخدادهای سامانه ثبت می‌گردد.

### 💡 گام‌ها و اقدامات پیشنهادی
1. بازبینی دوره‌ای سند توسط واحد مربوطه.
2. به‌روزرسانی نسخه در صورت تغییر محتوا.
3. تنظیم سطح دسترسی در صورت نیاز به مخاطبان جدید.
"""


def _call_gemini(settings: Settings, system: str, prompt: str) -> str | None:
    key = (settings.gemini_api_key or "").strip()
    if not key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    try:
        with httpx.Client(timeout=45.0) as client:
            res = client.post(
                url,
                params={"key": key},
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.3},
                },
            )
        if res.status_code >= 400:
            return None
        data = res.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        return text or None
    except Exception:
        return None


@router.post("/chat")
def chat_with_resources(
    payload: AiChatIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    raise HTTPException(status_code=410, detail="بخش گفت‌وگو با منابع حذف شده است.")
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="پیام خالی است.")
    files = _visible_files(db, user, payload.file_ids)
    admin = user.role == "system_admin"
    cards = []
    for f in files:
        cards.append(_file_card(f, _excerpt_from_file(settings, f), admin))
    overview = "\n\n".join(f"[منبع {i + 1}]\n{c}" for i, c in enumerate(cards)) or "منبعی در دسترس نیست."
    ai = get_or_create_ai_settings(db)
    history_txt = ""
    for item in (payload.history or [])[-6:]:
        role = "کاربر" if item.get("role") == "user" else "دستیار"
        history_txt += f"{role}: {item.get('content', '')}\n"
    system = ai.chat_prompt
    prompt = f"فهرست منابع در دسترس:\n{overview}\n\nتاریخچه:\n{history_txt}\nپرسش کاربر:\n{message}"
    reply = _call_gemini(settings, system, prompt) or _local_chat_reply(message, files)
    write_audit(
        db,
        user=user,
        action="ai_chat",
        target_resource="گفت‌وگو با منابع",
        details="پرسش از منابع مجاز کاربر",
        request=request,
    )
    return {"response": reply, "source": "gemini" if settings.gemini_api_key else "local_assistant"}


@router.post("/summarize")
def summarize_file(
    payload: AiSummarizeIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    file, access = get_visible_file(db, user, payload.file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="فایل یافت نشد.")
    excerpt = _excerpt_from_file(settings, file)
    ai = get_or_create_ai_settings(db)
    mode = payload.mode if payload.mode in {"executive", "technical", "bullet_points"} else "executive"
    card = _file_card(file, excerpt, user.role == "system_admin")
    prompt = f"حالت خلاصه: {mode}\n\nمشخصات سند:\n{card}"
    summary = _call_gemini(settings, ai.summarize_prompt, prompt) or _local_summary(file, excerpt, mode)
    write_audit(
        db,
        user=user,
        action="ai_summarize",
        target_resource=file.title,
        target_type="file",
        target_id=file.id,
        details="تولید خلاصه هوشمند",
        request=request,
    )
    return {"summary": summary, "source": "gemini" if settings.gemini_api_key else "local_assistant"}
