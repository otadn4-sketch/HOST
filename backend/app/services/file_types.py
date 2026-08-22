from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.security.constants import (
    DANGEROUS_EXTENSIONS,
    MAGIC_MAP,
    OFFICE_CONTENT_TYPES,
    OFFICE_MACRO_HINTS,
)

MAX_ZIP_FILES = 2000
MAX_ZIP_UNCOMPRESSED = 200 * 1024 * 1024
MAX_ZIP_RATIO = 100
MAX_NESTED_ZIP_DEPTH = 0  # office containers themselves are zip; nested zip entries are rejected


@dataclass
class DetectionResult:
    extension: str
    mime: str
    is_executable: bool
    is_office: bool
    has_macros: bool
    reason: str = ""


def normalize_extension(name: str) -> str:
    suffix = Path(name).suffix.lower().lstrip(".")
    return suffix


def looks_like_text(data: bytes) -> bool:
    if not data:
        return True
    if b"\x00" in data[:8192]:
        return False
    sample = data[:8192]
    if sample.startswith(b"\xff\xfe") or sample.startswith(b"\xfe\xff"):
        return True
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        try:
            sample.decode("cp1256")
            return True
        except UnicodeDecodeError:
            return False


def detect_type(path: Path, declared_name: str) -> DetectionResult:
    header = path.read_bytes()[:16]
    declared_ext = normalize_extension(declared_name)
    size = path.stat().st_size

    if header.startswith(b"MZ") or header.startswith(b"\x7fELF"):
        return DetectionResult(declared_ext or "exe", "application/octet-stream", True, False, False, "فایل اجرایی شناسایی شد")

    if header.startswith(b"#!"):
        return DetectionResult(declared_ext or "sh", "text/x-shellscript", True, False, False, "اسکریپت اجرایی شناسایی شد")

    if header.startswith(b"%PDF"):
        if declared_ext and declared_ext != "pdf":
            return DetectionResult("pdf", "application/pdf", False, False, False, "پسوند با نوع واقعی فایل همخوان نیست")
        return DetectionResult("pdf", "application/pdf", False, False, False)

    if header.startswith(b"PK"):
        return _inspect_zip(path, declared_ext)

    if declared_ext in DANGEROUS_EXTENSIONS:
        return DetectionResult(declared_ext, "application/octet-stream", True, False, False, "پسوند اجرایی مجاز نیست")

    if declared_ext in {"txt", "csv"} or looks_like_text(path.read_bytes()[:8192] if size else b""):
        if declared_ext in {"txt", "csv", ""}:
            mime = "text/plain" if declared_ext != "csv" else "text/csv"
            return DetectionResult(declared_ext or "txt", mime, False, False, False)

    return DetectionResult(
        declared_ext or "bin",
        "application/octet-stream",
        False,
        False,
        False,
        "نوع فایل شناسایی‌نشده است",
    )


def _inspect_zip(path: Path, declared_ext: str) -> DetectionResult:
    try:
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
            if len(infos) > MAX_ZIP_FILES:
                return DetectionResult(declared_ext, "application/zip", False, False, False, "تعداد فایل‌های داخل بسته از حد مجاز بیشتر است")
            uncompressed = sum(i.file_size for i in infos)
            compressed = sum(i.compress_size or 1 for i in infos)
            if uncompressed > MAX_ZIP_UNCOMPRESSED:
                return DetectionResult(declared_ext, "application/zip", False, False, False, "حجم uncompressed بسته بیش از حد مجاز است")
            if compressed and uncompressed / max(compressed, 1) > MAX_ZIP_RATIO:
                return DetectionResult(declared_ext, "application/zip", False, False, False, "نسبت فشرده‌سازی مشکوک (zip bomb)")
            names = []
            for info in infos:
                name = info.filename.replace("\\", "/")
                if name.startswith("/") or ".." in name.split("/"):
                    return DetectionResult(declared_ext, "application/zip", False, False, False, "مسیر غیرمجاز داخل بسته")
                if info.is_dir():
                    continue
                # zipfile sets external_attr; symlink/unix type bits
                is_symlink = (info.external_attr >> 16) & 0o170000 == 0o120000
                if is_symlink:
                    return DetectionResult(declared_ext, "application/zip", False, False, False, "پیوند نمادین داخل بسته مجاز نیست")
                names.append(name.lower())
                if name.lower().endswith(".zip"):
                    return DetectionResult(declared_ext, "application/zip", False, False, False, "بسته تودرتو مجاز نیست")

            joined = " ".join(names)
            has_macros = any(hint.lower() in joined for hint in OFFICE_MACRO_HINTS)
            for prefix, (ext, mime) in OFFICE_CONTENT_TYPES.items():
                if any(n.startswith(prefix) or f"{prefix}" in n for n in names):
                    if declared_ext and declared_ext != ext:
                        return DetectionResult(ext, mime, False, True, has_macros, "پسوند با نوع واقعی فایل همخوان نیست")
                    if has_macros:
                        return DetectionResult(ext, mime, False, True, True, "ماکرو آفیس شناسایی شد")
                    return DetectionResult(ext, mime, False, True, False)

            if declared_ext == "zip":
                return DetectionResult("zip", "application/zip", False, False, False, "فرمت zip در فهرست پیش‌فرض مجاز نیست مگر در سیاست")
            return DetectionResult(declared_ext or "zip", "application/zip", False, False, False, "بسته zip ناشناخته")
    except zipfile.BadZipFile:
        return DetectionResult(declared_ext, "application/octet-stream", False, False, False, "بسته آسیب‌دیده است")


def extension_allowed(ext: str, allowed: list[str]) -> bool:
    return ext.lower() in {e.lower().lstrip(".") for e in allowed}


def is_dangerous_extension(ext: str) -> bool:
    return ext.lower().lstrip(".") in DANGEROUS_EXTENSIONS
