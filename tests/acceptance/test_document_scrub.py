from app.services.document_scrub import apply_scrub, redact_text
from tests.conftest import auth_header, login, seed_user


def test_redact_email_phone_national_id_and_recommendation():
    text = "email a@b.com phone 09121234567 nid 0012345678\nپیشنهاد: اقدام فوری\n"
    out, count = redact_text(text, ["strip_recipient_details", "remove_recommendation_sections"])
    assert "a@b.com" not in out
    assert "09121234567" not in out
    assert "0012345678" not in out
    assert "اقدام فوری" not in out
    assert count >= 4


def test_pdf_scrub_is_fail_safe():
    result = apply_scrub(b"%PDF-1.4 fake", extension="pdf", mime="application/pdf", rules=["strip_pdf_metadata"])
    assert result["applied"] is False
    assert result["publication_ready"] is False
    assert result["status"] == "unavailable"
    assert result["output"] is None


def test_docx_scrub_redacts_and_unsupported_is_fail_safe():
    import io
    import zipfile

    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>email a@b.com پیشنهاد: محرمانه</w:t></w:r></w:p></w:body></w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", document)
    result = apply_scrub(
        buf.getvalue(),
        extension="docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        rules=["strip_recipient_details", "remove_recommendation_sections"],
    )
    assert result["applied"] is True
    assert result["publication_ready"] is True
    assert b"a@b.com" not in result["output"]
    exe = apply_scrub(b"MZ\x90not-a-doc", extension="exe", mime="application/octet-stream", rules=[])
    assert exe["applied"] is False
    assert exe["publication_ready"] is False


def test_scrub_job_creates_copy_and_leaves_original(client):
    seed_user("alice", "user", email="alice@eytan.local")
    login(client, "alice")
    h = auth_header(client)
    payload = "مخاطب: n@x.ir شماره 09120000000\n"
    up = client.post(
        "/api/files",
        headers=h,
        files={"file": ("secret.txt", payload.encode("utf-8"), "text/plain")},
        data={"title": "سند حساس", "topic": "آزمون", "classification": "internal"},
    )
    assert up.status_code == 200, up.text
    file_id = up.json()["file"]["id"]
    job = client.post("/api/scrub/jobs", headers=h, json={"file_id": file_id, "rules": ["strip_recipient_details"]})
    assert job.status_code == 200, job.text
    body = job.json()["job"]
    assert body["status"] == "completed"
    assert body["applied"] is True
    assert body["publication_ready"] is True
    assert body["redacted_count"] >= 1
    assert body["result_file_id"]
    original = client.get(f"/api/files/{file_id}/download", headers=h)
    assert original.status_code == 200
    assert b"n@x.ir" in original.content
    scrubbed = client.get(f"/api/files/{body['result_file_id']}/download", headers=h)
    assert scrubbed.status_code == 200
    assert b"n@x.ir" not in scrubbed.content
    assert "حذف" in scrubbed.content.decode("utf-8")
