import pytest

from app.config import (
    Settings,
    apply_production_locks,
    sms_outbound_allowed,
    unsigned_updates_allowed,
    validate_runtime_settings,
)


def test_production_rejects_insecure_defaults():
    settings = Settings(
        eytan_env="production",
        session_secret="insecure-dev-only-override-in-env",
        database_url="postgresql+psycopg://eytan:eytan@db:5432/eytan",
        backup_encryption_key="0" * 64,
        sms_enabled=True,
        clamav_disabled=True,
        scan_fail_closed=False,
    )
    with pytest.raises(RuntimeError, match="insecure production configuration"):
        validate_runtime_settings(settings)


def test_production_locks_sms_and_unsigned():
    settings = Settings(
        eytan_env="production",
        sms_enabled=True,
        update_allow_unsigned=True,
        automated_delivery_enabled=True,
    )
    apply_production_locks(settings)
    assert settings.sms_enabled is False
    assert settings.update_allow_unsigned is False
    assert settings.automated_delivery_enabled is False
    assert sms_outbound_allowed(settings) is False
    assert unsigned_updates_allowed(settings) is False


def test_development_can_enable_sms_flag():
    settings = Settings(eytan_env="development", sms_enabled=True)
    assert sms_outbound_allowed(settings) is True
    validate_runtime_settings(settings)
