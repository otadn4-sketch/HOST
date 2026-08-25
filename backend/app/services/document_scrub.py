from __future__ import annotations

import hashlib
import io
import re
import zipfile
from pathlib import Path

REDACTION = "[حذف‌شده]"

SUPPORTED_RULES = (
    "strip_recipient_details",
    "remove_recommendation_sections",
    "strip_pdf_metadata",
    "strip_office_metadata",
)

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
IRAN_MOBILE_RE = re.compile(r"(?:\+98|0098|0)?9\d{9}\b")
NATIONAL_ID_RE = re.compile(r"\b\d{10}\b")
RECOMMENDATION_LINE_RE = re.compile(r"(?im)^.*پیشنهاد.*$")

TEXT_EXTENSIONS = {"txt", "csv", "md", "html", "htm"}
OFFICE_EXTENSIONS = {"docx"}
PDF_EXTENSIONS = {"pdf"}


def plan_scrub(rules: list[str] | None) -> dict:
    selected = [r for r in (rules or []) if r in SUPPORTED_RULES]
    if not selected:
        selected = ["strip_recipient_details", "remove_recommendation_sections"]
    return {
        "status": "planned",
        "applied": False,
        "rules": selected,
        "note": "پالایش فقط روی قالب‌های پشتیبانی‌شده اعمال می‌شود؛ در غیر این صورت فایل بدون تغییر و ناامن تلقی نمی‌شود.",
    }


def redact_text(text: str, rules: list[str]) -> tuple[str, int]:
    count = 0
    out = text
    if "strip_recipient_details" in rules:
        out, n = EMAIL_RE.subn(REDACTION, out)
        count += n
        out, n = IRAN_MOBILE_RE.subn(REDACTION, out)
        count += n
        out, n = NATIONAL_ID_RE.subn(REDACTION, out)
        count += n
    if "remove_recommendation_sections" in rules:
        out, n = RECOMMENDATION_LINE_RE.subn(REDACTION, out)
        count += n
    return out, count


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1256", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _scrub_docx(data: bytes, rules: list[str]) -> tuple[bytes, int, str]:
    try:
        src = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"بسته آفیس نامعتبر است: {exc}") from exc
    redacted = 0
    out_buf = io.BytesIO()
    with zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as dest:
        for info in src.infolist():
            payload = src.read(info.filename)
            name = info.filename.replace("\\", "/")
            if name.startswith("word/") and name.endswith(".xml"):
                text = payload.decode("utf-8", errors="replace")
                text, n = redact_text(text, rules)
                redacted += n
                payload = text.encode("utf-8")
            elif "strip_office_metadata" in rules and name.startswith("docProps/") and name.endswith(".xml"):
                text = payload.decode("utf-8", errors="replace")
                cleaned, n = redact_text(text, ["strip_recipient_details"])
                # Drop common identity fields without pretending full forensic wipe.
                cleaned = re.sub(r"(<(?:[A-Za-z0-9]+:)?(?:creator|lastModifiedBy|manager|company)>)([^<]*)(</)", rf"\1{REDACTION}\3", cleaned)
                redacted += n + (0 if cleaned == text else 1)
                payload = cleaned.encode("utf-8")
            dest.writestr(info, payload)
    src.close()
    return out_buf.getvalue(), redacted, "پالایش متن سند آفیس انجام شد."


def apply_scrub(data: bytes, *, extension: str, mime: str, rules: list[str]) -> dict:
    selected = [r for r in rules if r in SUPPORTED_RULES]
    if not selected:
        selected = ["strip_recipient_details", "remove_recommendation_sections"]
    ext = (extension or "").lower().lstrip(".")
    mime = (mime or "").lower()

    if ext in PDF_EXTENSIONS or mime == "application/pdf":
        return {
            "status": "unavailable",
            "applied": False,
            "rules": selected,
            "redacted_count": 0,
            "output": None,
            "note": "پالایش PDF در این نسخه fail-safe است: بدون کتابخانهٔ کامل متادیتا، فایل تغییر داده نشد و امن تلقی نمی‌شود.",
        }

    if ext in OFFICE_EXTENSIONS or mime in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }:
        try:
            output, count, note = _scrub_docx(data, selected)
        except ValueError as exc:
            return {
                "status": "failed",
                "applied": False,
                "rules": selected,
                "redacted_count": 0,
                "output": None,
                "note": str(exc),
            }
        return {
            "status": "completed",
            "applied": True,
            "rules": selected,
            "redacted_count": count,
            "output": output,
            "note": note,
        }

    if ext in TEXT_EXTENSIONS or mime.startswith("text/"):
        text, count = redact_text(_decode_text(data), selected)
        return {
            "status": "completed",
            "applied": True,
            "rules": selected,
            "redacted_count": count,
            "output": text.encode("utf-8"),
            "note": "پالایش متن ساده انجام شد.",
        }

    return {
        "status": "unavailable",
        "applied": False,
        "rules": selected,
        "redacted_count": 0,
        "output": None,
        "note": "قالب فایل برای پالایش پشتیبانی نمی‌شود؛ فایل اصلی تغییر نکرد و امن تلقی نشد.",
    }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
