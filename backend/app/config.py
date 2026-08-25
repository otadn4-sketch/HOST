from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


INSECURE_SECRET_VALUES = {
    "",
    "change-me-in-production",
    "change-me-with-a-long-random-value",
    "insecure-dev-only-override-in-env",
    "secret",
    "password",
    "admin",
}

INSECURE_DATABASE_MARKERS = (
    "eytan:eytan@",
    "change-me-with-a-long-random-value",
    "change-me-in-production",
    "postgres:postgres@",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    eytan_env: str = "production"
    public_host: str = "localhost"
    public_origin: str = "https://localhost"
    cors_origins: str = "https://localhost"

    database_url: str = ""
    session_secret: str = ""

    default_max_file_size_bytes: int = 52_428_800
    vault_path: Path = Path("/var/lib/eytan/vault")
    quarantine_path: Path = Path("/var/lib/eytan/quarantine")
    backup_path: Path = Path("/var/lib/eytan/backups")
    releases_path: Path = Path("/var/lib/eytan/releases")
    staging_path: Path = Path("/var/lib/eytan/staging")

    clamd_host: str = "clamav"
    clamd_port: int = 3310
    scan_fail_closed: bool = True
    clamav_disabled: bool = False

    update_public_key: str = ""
    update_agent_token: str = ""
    update_agent_url: str = "http://update-agent:8787"
    update_allow_unsigned: bool = False
    backup_encryption_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    eytan_seed_dev: bool = False
    dev_admin_password: str = ""
    dev_group_admin_password: str = ""
    dev_user_password: str = ""
    dev_viewer_password: str = ""

    session_cookie_name: str = "eytan_session"
    csrf_cookie_name: str = "eytan_csrf"
    session_secure_cookie: bool = True

    # Product rule: automated messenger/SMS delivery stays off until a written decision.
    automated_delivery_enabled: bool = False
    phase_1_archive_enabled: bool = True
    phase_2_meetings_enabled: bool = True
    phase_3_recipient_profiles_enabled: bool = True
    phase_4_sharing_enabled: bool = False
    phase_5_security_graph_enabled: bool = False

    sms_enabled: bool = False
    sms_base_url: str = ""
    sms_api_key: str = ""
    sms_sender: str = ""
    sms_http_method: str = "POST"
    sms_content_type: str = "json"
    sms_url_template: str = ""
    sms_body_template: str = ""
    sms_auth_header_name: str = ""
    sms_timeout_seconds: int = 15

    faran_enabled: bool = False
    faran_base_url: str = ""
    faran_api_token: str = ""
    faran_allow_network: bool = False

    @property
    def is_production(self) -> bool:
        return self.eytan_env.lower() == "production"

    @property
    def cors_origin_list(self) -> List[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


def apply_production_locks(settings: Settings) -> None:
    """Hard-disable outbound messaging and unsigned updates in production."""
    if not settings.is_production:
        return
    settings.sms_enabled = False
    settings.automated_delivery_enabled = False
    settings.update_allow_unsigned = False


def sms_outbound_allowed(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if settings.is_production:
        return False
    return bool(settings.sms_enabled)


def unsigned_updates_allowed(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if settings.is_production:
        return False
    return bool(settings.update_allow_unsigned)


def validate_runtime_settings(settings: Settings) -> None:
    if not settings.is_production:
        return
    problems: list[str] = []
    secret = (settings.session_secret or "").strip()
    if secret in INSECURE_SECRET_VALUES or len(secret) < 32:
        problems.append("SESSION_SECRET must be a unique value at least 32 characters (no sample placeholder)")
    db = settings.database_url or ""
    if not db.strip():
        problems.append("DATABASE_URL is required in production")
    elif any(marker in db for marker in INSECURE_DATABASE_MARKERS):
        problems.append("DATABASE_URL still contains a sample or default credential")
    bak = (settings.backup_encryption_key or "").strip()
    if len(bak) < 64 or bak == "change-me-64-hex-chars" or bak == "0" * 64:
        problems.append("BACKUP_ENCRYPTION_KEY must be a unique 64-hex value (no sample placeholder)")
    if settings.sms_enabled:
        problems.append("SMS_ENABLED must remain false in production until a written decision")
    if settings.automated_delivery_enabled:
        problems.append("AUTOMATED_DELIVERY_ENABLED must remain false in production")
    if settings.update_allow_unsigned:
        problems.append("unsigned updates are not allowed in production")
    if settings.clamav_disabled:
        problems.append("CLAMAV_DISABLED cannot be true in production")
    if not settings.scan_fail_closed:
        problems.append("SCAN_FAIL_CLOSED must be true in production")
    if problems:
        raise RuntimeError("insecure production configuration: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()
