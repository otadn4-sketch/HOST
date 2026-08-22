from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.security.passwords import hash_password
from app.security.rate_limit import limiter


STRONG = "Str0ng-Passw0rd!"


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "eytan.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db}")
    monkeypatch.setenv("EYTAN_ENV", "development")
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-value-32bytes-min")
    monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
    monkeypatch.setenv("QUARANTINE_PATH", str(tmp_path / "quarantine"))
    monkeypatch.setenv("BACKUP_PATH", str(tmp_path / "backups"))
    monkeypatch.setenv("STAGING_PATH", str(tmp_path / "staging"))
    monkeypatch.setenv("RELEASES_PATH", str(tmp_path / "releases"))
    monkeypatch.setenv("CLAMAV_DISABLED", "true")
    monkeypatch.setenv("SCAN_FAIL_CLOSED", "false")
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "0" * 64)
    monkeypatch.setenv("CORS_ORIGINS", "http://testserver")
    get_settings.cache_clear()
    from app.api import deps

    deps._engine = None
    deps._SessionLocal = None
    limiter.clear()
    from app.main import create_app

    application = create_app()
    with TestClient(application) as c:
        yield c
    get_settings.cache_clear()
    limiter.clear()


def seed_user(username: str, role: str, password: str = STRONG, email: str | None = None):
    from app.api.deps import _SessionLocal
    from app.models.entities import Group, User

    db = _SessionLocal()
    try:
        group = db.query(Group).filter(Group.code == "SEC-IT").one()
        user = User(
            username=username,
            full_name=username,
            email=email or f"{username}@eytan.local",
            password_hash=hash_password(password),
            role=role,
            group_id=group.id,
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id, user.group_id
    finally:
        db.close()


def login(client: TestClient, username: str, password: str = STRONG):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    return res


def auth_header(client: TestClient) -> dict[str, str]:
    csrf = client.cookies.get("eytan_csrf") or ""
    return {"X-CSRF-Token": csrf}
