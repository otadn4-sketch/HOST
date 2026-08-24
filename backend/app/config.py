from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    eytan_env: str = "production"
    public_host: str = "localhost"
    public_origin: str = "https://localhost"
    cors_origins: str = "https://localhost"

    database_url: str = "postgresql+psycopg://eytan:eytan@db:5432/eytan"
    session_secret: str = "insecure-dev-only-override-in-env"

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

    # Product roadmap: automated messenger/SMS delivery is permanently off.
    automated_delivery_enabled: bool = False
    phase_1_archive_enabled: bool = True
    phase_2_meetings_enabled: bool = True
    phase_3_recipient_profiles_enabled: bool = True
    phase_4_sharing_enabled: bool = True
    phase_5_security_graph_enabled: bool = True

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
