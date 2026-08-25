from tests.conftest import auth_header, login, seed_user


def test_admin_download_preview_and_unique_views(client):
    seed_user("admin", "system_admin")
    seed_user("alice", "user", email="alice@eytan.local")

    login(client, "alice")
    h = auth_header(client)
    up = client.post(
        "/api/files",
        headers=h,
        files={"file": ("ok.txt", "متن پیش‌نمایش\n".encode("utf-8"), "text/plain")},
        data={"title": "سند پیش‌نمایش", "topic": "آزمون", "classification": "internal"},
    )
    assert up.status_code == 200, up.text
    file_id = up.json()["file"]["id"]

    for _ in range(3):
        preview = client.get(f"/api/files/{file_id}/preview", headers=h)
        assert preview.status_code == 200
        assert "متن پیش‌نمایش".encode("utf-8") in preview.content
        assert "inline" in preview.headers.get("content-disposition", "")

    client.post("/api/auth/logout", headers=h)

    login(client, "admin")
    ha = auth_header(client)
    listed = client.get("/api/files", headers=ha)
    match = next(item for item in listed.json()["files"] if item["id"] == file_id)
    assert match["can_download"] is True
    download = client.get(f"/api/files/{file_id}/download", headers=ha)
    assert download.status_code == 200
    assert download.content == "متن پیش‌نمایش\n".encode("utf-8")

    from app.api.deps import _SessionLocal
    from app.models.entities import FileObject

    db = _SessionLocal()
    try:
        row = db.query(FileObject).filter(FileObject.id == file_id).one()
        row.scan_status = "suspicious"
        row.quarantine_reason = "پویش بدافزار در دسترس نبود (connection refused)"
        db.commit()
    finally:
        db.close()

    suspicious_dl = client.get(f"/api/files/{file_id}/download", headers=ha)
    assert suspicious_dl.status_code in {403, 404}

    malware_up = client.post(
        "/api/files",
        headers=ha,
        files={"file": ("malware.pdf", b"MZ\x90\x00not-a-pdf", "application/pdf")},
        data={"title": "بدافزار", "topic": "آزمون", "classification": "internal"},
    )
    assert malware_up.status_code == 200
    qid = malware_up.json()["file"]["id"]
    db = _SessionLocal()
    try:
        row = db.query(FileObject).filter(FileObject.id == qid).one()
        row.scan_status = "quarantined"
        row.quarantine_reason = "شناسایی بدافزار: Eicar-Test-Signature"
        db.commit()
    finally:
        db.close()
    malware_dl = client.get(f"/api/files/{qid}/download", headers=ha)
    assert malware_dl.status_code in {403, 404}

    dash = client.get("/api/dashboard?range=all", headers=ha)
    assert dash.status_code == 200
    kpis = dash.json()["kpis"]
    assert kpis["views_total"] == 3
    assert kpis["views_unique"] == 1
    chart = dash.json()["file_viewer_chart"]
    assert chart
    assert any(row.get("alice") == 3 for row in chart)
    logs = client.get("/api/logs", headers=ha)
    actions = [item["action"] for item in logs.json()["logs"]]
    assert "file_preview" in actions
    assert any(item["action_title"] == "پیش‌نمایش محتوای فایل" for item in logs.json()["logs"])


def _docx_bytes(text: str) -> bytes:
    import zipfile
    from io import BytesIO

    buf = BytesIO()
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        zf.writestr("word/document.xml", document)
    return buf.getvalue()


def test_docx_preview_returns_extracted_text_not_zip(client):
    seed_user("alice", "user", email="alice@eytan.local")
    login(client, "alice")
    h = auth_header(client)
    up = client.post(
        "/api/files",
        headers=h,
        files={"file": ("report.docx", _docx_bytes("متن استخراج‌شده از ورد"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"title": "گزارش ورد", "topic": "آزمون", "classification": "internal"},
    )
    assert up.status_code == 200, up.text
    file_id = up.json()["file"]["id"]
    preview = client.get(f"/api/files/{file_id}/preview", headers=h)
    assert preview.status_code == 200, preview.text
    body = preview.content.decode("utf-8")
    assert "متن استخراج‌شده از ورد" in body
    assert not body.startswith("PK")
    assert "[Content_Types].xml" not in body
    assert preview.headers.get("x-eytan-preview") == "extracted-text"
    assert "text/plain" in preview.headers.get("content-type", "")
