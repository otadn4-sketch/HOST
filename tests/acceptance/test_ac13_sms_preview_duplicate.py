from unittest.mock import patch

from app.config import get_settings
from tests.conftest import auth_header, login, seed_user


def test_duplicate_similar_filename_rejected(client):
    seed_user("alice", "user", email="alice@eytan.local")
    login(client, "alice")
    h = auth_header(client)
    first = client.post(
        "/api/files",
        headers=h,
        files={"file": ("Report Final.TXT", "one\n".encode("utf-8"), "text/plain")},
        data={"title": "گزارش نهایی", "topic": "آزمون", "classification": "internal"},
    )
    assert first.status_code == 200, first.text
    dup = client.post(
        "/api/files",
        headers=h,
        files={"file": ("report   final.txt", "two\n".encode("utf-8"), "text/plain")},
        data={"title": "گزارش دیگر", "topic": "آزمون", "classification": "internal"},
    )
    assert dup.status_code == 409
    assert "نام مشابه" in dup.text


def test_preview_heartbeat_does_not_inflate_visits(client):
    seed_user("admin", "system_admin")
    seed_user("alice", "user", email="alice@eytan.local")
    login(client, "alice")
    h = auth_header(client)
    up = client.post(
        "/api/files",
        headers=h,
        files={"file": ("ok.txt", "متن\n".encode("utf-8"), "text/plain")},
        data={"title": "سند نبض", "topic": "آزمون", "classification": "internal"},
    )
    assert up.status_code == 200, up.text
    file_id = up.json()["file"]["id"]
    preview = client.get(f"/api/files/{file_id}/preview", headers=h)
    assert preview.status_code == 200
    beat = client.post(f"/api/files/{file_id}/preview-heartbeat", headers=h)
    assert beat.status_code == 200, beat.text
    beat2 = client.post(f"/api/files/{file_id}/preview-heartbeat", headers=h)
    assert beat2.status_code == 200
    client.post("/api/auth/logout", headers=h)
    login(client, "admin")
    ha = auth_header(client)
    dash = client.get("/api/dashboard?range=all", headers=ha)
    assert dash.status_code == 200
    kpis = dash.json()["kpis"]
    assert kpis["views_total"] == 1
    assert kpis["views_unique"] == 1
    assert kpis["live_previews"] >= 1
    assert dash.json()["live_previews"]


def test_sms_disabled_by_default_rejects_send_without_network(client):
    seed_user("admin", "system_admin")
    login(client, "admin")
    h = auth_header(client)
    cfg = client.get("/api/sms/config", headers=h)
    assert cfg.status_code == 200, cfg.text
    body = cfg.json()["config"]
    assert body["enabled"] is False
    assert body["outbound_allowed"] is False
    enable = client.put(
        "/api/sms/config",
        headers=h,
        json={
            "enabled": True,
            "base_url": "https://sms.example.local/send",
            "api_key": "test-key-12345",
            "sender": "1000",
        },
    )
    assert enable.status_code == 403
    with patch("app.services.sms._http_send", return_value=(200, '{"ok":true}')) as mocked:
        sent = client.post(
            "/api/sms/send",
            headers=h,
            json={"message": "متن نمایش داده شده", "phones": ["09120000000"]},
        )
        assert sent.status_code == 403, sent.text
        mocked.assert_not_called()
    directory = client.get("/api/sms/directory", headers=h)
    assert directory.status_code == 403


def test_sms_send_mocked_only_when_non_production_flag_on(client):
    seed_user("admin", "system_admin")
    login(client, "admin")
    h = auth_header(client)
    settings = get_settings()
    settings.sms_enabled = True
    settings.eytan_env = "development"
    cfg = client.put(
        "/api/sms/config",
        headers=h,
        json={
            "enabled": True,
            "base_url": "https://sms.example.local/send",
            "api_key": "test-key-12345",
            "sender": "1000",
            "http_method": "POST",
            "content_type": "json",
        },
    )
    assert cfg.status_code == 200, cfg.text
    body = cfg.json()["config"]
    assert body["enabled"] is True
    assert body["outbound_allowed"] is True
    assert "test-key-12345" not in str(body.get("api_key_masked"))
    with patch("app.services.sms._http_send", return_value=(200, '{"ok":true}')) as mocked:
        sent = client.post(
            "/api/sms/send",
            headers=h,
            json={"message": "متن نمایش داده شده", "phones": ["09120000000"]},
        )
        assert sent.status_code == 200, sent.text
        assert sent.json()["sent"] == 1
        mocked.assert_called_once()
    settings.sms_enabled = False

