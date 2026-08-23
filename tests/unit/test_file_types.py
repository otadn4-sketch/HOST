from pathlib import Path

from app.services.file_types import detect_type, is_dangerous_extension


def test_pdf_magic(tmp_path: Path):
    p = tmp_path / "a.bin"
    p.write_bytes(b"%PDF-1.7\n1 0 obj\n")
    d = detect_type(p, "report.pdf")
    assert d.extension == "pdf"
    assert not d.is_executable


def test_exe_magic(tmp_path: Path):
    p = tmp_path / "a.pdf"
    p.write_bytes(b"MZ\x90\x00this is not a pdf")
    d = detect_type(p, "invoice.pdf")
    assert d.is_executable


def test_elf_magic(tmp_path: Path):
    p = tmp_path / "tool.txt"
    p.write_bytes(b"\x7fELF\x02\x01")
    d = detect_type(p, "tool.txt")
    assert d.is_executable


def test_shebang(tmp_path: Path):
    p = tmp_path / "x.sh"
    p.write_text("#!/bin/sh\necho hi\n")
    d = detect_type(p, "x.sh")
    assert d.is_executable


def test_txt(tmp_path: Path):
    p = tmp_path / "note.txt"
    p.write_text("گزارش داخلی\n", encoding="utf-8")
    d = detect_type(p, "note.txt")
    assert d.extension == "txt"
    assert not d.is_executable


def test_zip_bomb_ratio(tmp_path: Path):
    import zipfile

    z = tmp_path / "bomb.zip"
    with zipfile.ZipFile(z, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("zeros.bin", b"\x00" * 2_000_000)
    d = detect_type(z, "bomb.zip")
    assert "zip bomb" in d.reason or "uncompressed" in d.reason or d.reason


def test_path_traversal_in_zip(tmp_path: Path):
    import zipfile

    z = tmp_path / "trav.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("../etc/passwd", "x")
    d = detect_type(z, "file.docx")
    assert "مسیر" in d.reason or d.reason


def test_dangerous_ext():
    assert is_dangerous_extension("exe")
    assert is_dangerous_extension(".ps1")
    assert not is_dangerous_extension("pdf")


def _make_docx(path: Path, text: str) -> Path:
    import zipfile

    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", types)
        zf.writestr("word/document.xml", document)
    return path


def test_office_preview_extracts_docx_text(tmp_path: Path):
    from app.services.file_types import extract_office_preview_text

    path = _make_docx(tmp_path / "note.docx", "گزارش داخلی ایتان")
    text = extract_office_preview_text(path, "docx")
    assert text is not None
    assert "گزارش داخلی ایتان" in text
    assert not text.startswith("PK")


def test_office_preview_xlsx_and_pptx(tmp_path: Path):
    import zipfile

    from app.services.file_types import extract_office_preview_text

    xlsx = tmp_path / "t.xlsx"
    with zipfile.ZipFile(xlsx, "w") as zf:
        zf.writestr(
            "xl/sharedStrings.xml",
            '<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<si><t>بودجه سالانه</t></si></sst>",
        )
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>',
        )
    assert "بودجه سالانه" in (extract_office_preview_text(xlsx, "xlsx") or "")

    pptx = tmp_path / "t.pptx"
    with zipfile.ZipFile(pptx, "w") as zf:
        zf.writestr(
            "ppt/slides/slide1.xml",
            '<?xml version="1.0"?><p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            "<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>اسلاید اول</a:t></a:r></a:p></p:txBody></p:sp>"
            "</p:spTree></p:cSld></p:sld>",
        )
    assert "اسلاید اول" in (extract_office_preview_text(pptx, "pptx") or "")
