from pathlib import Path


REQUIRED_COMPOSE_KEYS = (
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "PUBLIC_HOST",
    "CLIENT_MAX_BODY_SIZE",
    "TLS_CERT_PATH",
    "TLS_KEY_PATH",
    "SESSION_SECRET",
    "UPDATE_AGENT_TOKEN",
    "BACKUP_ENCRYPTION_KEY",
)


def test_env_example_has_no_usable_secrets_and_matches_compose():
    root = Path("/workspace")
    env = (root / ".env.example").read_text()
    assert "ChangeMe_Admin_123!" not in env
    assert "eytan:eytan@" not in env
    assert "SECRET_KEY=change-me-in-production" not in env
    assert "BOOTSTRAP_ADMIN_PASSWORD" not in env
    assert "SMS_ENABLED=false" in env
    assert "AUTOMATED_DELIVERY_ENABLED=false" in env
    assert "PHASE_5_SECURITY_GRAPH_ENABLED=false" in env
    assert "SCAN_FAIL_CLOSED=true" in env
    assert "POSTGRES_PASSWORD=change-me-with-a-long-random-value" in env
    assert "SESSION_SECRET=change-me-with-a-long-random-value" in env
    compose = (root / "docker-compose.yml").read_text()
    for key in REQUIRED_COMPOSE_KEYS:
        assert f"{key}=" in env or f"${{{key}" in compose
        if f"${{{key}" in compose or f"${{{key}:" in compose:
            assert f"{key}=" in env
