from tests.conftest import auth_header, login, seed_user


def test_ac03_upload_validation_and_quarantine(client):
    seed_user("admin", "system_admin")
    seed_user("alice", "user", email="alice@eytan.local")
    login(client, "admin")
    ha = auth_header(client)
    client.put("/api/settings/policy", headers=ha, json={"max_file_size_bytes": 4096, "allowed_extensions": ["txt", "pdf"]})
    client.post("/api/auth/logout", headers=ha)

    login(client, "alice")
    h = auth_header(client)

    txt = client.post(
        "/api/files",
        headers=h,
        files={"file": ("ok.txt", "سلام سند\n".encode("utf-8"), "text/plain")},
        data={"title": "سند سالم", "topic": "آزمون", "classification": "internal"},
    )
    assert txt.status_code == 200, txt.text
    assert txt.json()["file"]["checksum_sha256"]
    assert len(txt.json()["file"]["checksum_sha256"]) == 64

    exe = client.post(
        "/api/files",
        headers=h,
        files={"file": ("malware.pdf", b"MZ\x90\x00not-a-pdf", "application/pdf")},
        data={"title": "بدافزار", "topic": "آزمون", "classification": "internal"},
    )
    assert exe.status_code == 200
    assert exe.json()["file"]["scan_status"] == "quarantined"
    qid = exe.json()["file"]["id"]
    dl = client.get(f"/api/files/{qid}/download", headers=h)
    assert dl.status_code in {403, 404}

    huge = client.post(
        "/api/files",
        headers=h,
        files={"file": ("big.txt", b"a" * 8000, "text/plain")},
        data={"title": "حجم زیاد", "topic": "آزمون"},
    )
    assert huge.status_code == 413
