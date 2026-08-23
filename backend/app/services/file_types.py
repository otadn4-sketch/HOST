from __future__ import annotations

import io
import zipfile
import xml.etree.ElementTree as ET
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


MAX_PREVIEW_XML_BYTES = 8 * 1024 * 1024
MAX_PREVIEW_CHARS = 80_000


def extract_office_preview_text(path: Path, extension: str = "") -> str | None:
    """Return readable text from OOXML (docx/xlsx/pptx). ZIP bytes are never returned."""
    ext = _office_preview_extension(path, extension)
    if ext not in {"docx", "xlsx", "pptx"}:
        return None
    try:
        with zipfile.ZipFile(path) as zf:
            if ext == "docx":
                text = _docx_preview_text(zf)
            elif ext == "xlsx":
                text = _xlsx_preview_text(zf)
            else:
                text = _pptx_preview_text(zf)
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError, ValueError):
        return None
    text = (text or "").strip()
    if not text:
        return None
    return _clip_preview(text)


def _office_preview_extension(path: Path, extension: str) -> str:
    ext = (extension or "").lower().lstrip(".")
    if ext in {"docx", "xlsx", "pptx"}:
        return ext
    try:
        with zipfile.ZipFile(path) as zf:
            names = [name.replace("\\", "/").lower() for name in zf.namelist()]
    except zipfile.BadZipFile:
        return ext
    if any(name.startswith("word/") for name in names):
        return "docx"
    if any(name.startswith("xl/") for name in names):
        return "xlsx"
    if any(name.startswith("ppt/") for name in names):
        return "pptx"
    return ext


def _clip_preview(text: str) -> str:
    if len(text) <= MAX_PREVIEW_CHARS:
        return text
    return text[:MAX_PREVIEW_CHARS] + "\n\n… (متن کوتاه‌شده برای پیش‌نمایش)"


def _xml_local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _read_zip_xml(zf: zipfile.ZipFile, name: str) -> ET.Element:
    info = zf.getinfo(name)
    if info.file_size > MAX_PREVIEW_XML_BYTES:
        raise ValueError("xml too large")
    return ET.fromstring(zf.read(name))


def _docx_preview_text(zf: zipfile.ZipFile) -> str:
    name = next((n for n in zf.namelist() if n.replace("\\", "/").lower() == "word/document.xml"), None)
    if not name:
        return ""
    root = _read_zip_xml(zf, name)
    lines: list[str] = []
    for paragraph in root.iter():
        if _xml_local(paragraph.tag) != "p":
            continue
        pieces = [node.text or "" for node in paragraph.iter() if _xml_local(node.tag) == "t"]
        line = "".join(pieces).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _xlsx_preview_text(zf: zipfile.ZipFile) -> str:
    names = [n.replace("\\", "/") for n in zf.namelist()]
    shared: list[str] = []
    shared_name = next((n for n in names if n.lower() == "xl/sharedstrings.xml"), None)
    if shared_name:
        root = _read_zip_xml(zf, shared_name)
        for si in root.iter():
            if _xml_local(si.tag) != "si":
                continue
            shared.append("".join(node.text or "" for node in si.iter() if _xml_local(node.tag) == "t"))
    sheets = sorted(n for n in names if n.lower().startswith("xl/worksheets/sheet") and n.lower().endswith(".xml"))
    lines: list[str] = []
    for sheet in sheets[:20]:
        root = _read_zip_xml(zf, sheet)
        lines.append(f"[{sheet.rsplit('/', 1)[-1]}]")
        for row in root.iter():
            if _xml_local(row.tag) != "row":
                continue
            cells: list[str] = []
            for cell in row:
                if _xml_local(cell.tag) != "c":
                    continue
                cell_type = cell.attrib.get("t", "")
                inline = None
                value = None
                for child in cell:
                    local = _xml_local(child.tag)
                    if local == "is":
                        inline = "".join(node.text or "" for node in child.iter() if _xml_local(node.tag) == "t")
                    elif local == "v":
                        value = child.text or ""
                if inline:
                    cells.append(inline)
                elif value:
                    if cell_type == "s":
                        try:
                            cells.append(shared[int(value)])
                        except (ValueError, IndexError):
                            cells.append(value)
                    else:
                        cells.append(value)
            if any(item.strip() for item in cells):
                lines.append("\t".join(cells))
            if sum(len(item) for item in lines) > MAX_PREVIEW_CHARS:
                break
    return "\n".join(lines)


def _pptx_preview_text(zf: zipfile.ZipFile) -> str:
    names = sorted(
        n
        for n in zf.namelist()
        if n.replace("\\", "/").lower().startswith("ppt/slides/slide")
        and n.lower().endswith(".xml")
        and "/_rels/" not in n.replace("\\", "/").lower()
    )
    parts: list[str] = []
    for index, name in enumerate(names[:40], 1):
        root = _read_zip_xml(zf, name)
        texts = [node.text.strip() for node in root.iter() if _xml_local(node.tag) == "t" and (node.text or "").strip()]
        if texts:
            parts.append(f"— اسلاید {index} —\n" + "\n".join(texts))
    return "\n\n".join(parts)
