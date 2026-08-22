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
