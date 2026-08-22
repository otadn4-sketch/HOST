from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class RecoveryRequestIn(BaseModel):
    username: str


class RecoveryConfirmIn(BaseModel):
    token: str
    new_password: str


class UserOut(ORMModel):
    id: str
    username: str
    full_name: str
    email: str
    phone_number: Optional[str] = None
    role: str
    group_id: Optional[str] = None
    department_id: Optional[str] = None
    department_name: str = ""
    status: str
    last_login: Optional[str] = None
    created_at: datetime
    must_change_password: bool = False


class UserCreateIn(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    full_name: str
    email: str
    phone_number: Optional[str] = None
    role: str
    group_id: Optional[str] = None
    password: str
    status: str = "active"


class UserPatchIn(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None
    group_id: Optional[str] = None
    status: Optional[str] = None


class ResetPasswordIn(BaseModel):
    new_password: str


class GroupOut(ORMModel):
    id: str
    name: str
    code: str
    description: str
    manager_id: Optional[str] = None
    manager_name: str = ""
    members_count: int = 0
    allowed_file_extensions: list[str] = []
    max_file_size_mb: int
    default_classification: str
    is_active: bool = True


class GroupCreateIn(BaseModel):
    name: str
    code: str
    description: str = ""
    manager_id: Optional[str] = None
    max_file_size_mb: int = 50
    allowed_file_extensions: list[str] = []
    default_classification: str = "internal"


class GroupPatchIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    manager_id: Optional[str] = None
    max_file_size_mb: Optional[int] = None
    allowed_file_extensions: Optional[list[str]] = None
    default_classification: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionIn(BaseModel):
    target_type: str
    target_id: str
    can_view: bool = True
    can_download: bool = False
    can_upload: bool = False
    can_manage: bool = False


class FileOut(ORMModel):
    id: str
    title: str
    original_name: str
    stored_vault_name: str
    topic: str
    department_id: Optional[str] = None
    department_name: str = ""
    uploader_id: str
    uploader_name: str = ""
    size_bytes: int
    mime_type: str
    extension: str
    version: str
    version_number: int
    parent_file_id: Optional[str] = None
    classification: str
    scan_status: str
    quarantine_reason: Optional[str] = None
    download_count: int
    view_count: int
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime
    checksum_sha256: str
    description: str = ""
    can_download: bool = False
    can_manage: bool = False
    permissions: list[dict[str, Any]] = []


class FileMetaPatchIn(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None
    description: Optional[str] = None
    classification: Optional[str] = None
    tags: Optional[list[str]] = None
    permissions: Optional[list[PermissionIn]] = None


class AuditLogOut(ORMModel):
    id: str
    timestamp: datetime
    user_id: Optional[str] = None
    username: str
    user_role: str
    action: str
    action_title: str
    target_resource: str
    details: str
    ip_address: str
    user_agent: Optional[str] = None
    severity: str


class PolicyOut(ORMModel):
    allowed_extensions: list[str]
    max_file_size_bytes: int
    clamav_scan_enabled: bool
    quarantine_dangerous_files: bool
    session_timeout_minutes: int
    max_failed_login_attempts: int
    lockout_duration_minutes: int
    password_min_length: int
    require_special_chars: bool
    vault_storage_path: str = "(server-side, not exposed)"
    allow_direct_path_access: bool = False
    enforce_https: bool = True


class PolicyPatchIn(BaseModel):
    allowed_extensions: Optional[list[str]] = None
    max_file_size_bytes: Optional[int] = None
    clamav_scan_enabled: Optional[bool] = None
    quarantine_dangerous_files: Optional[bool] = None
    session_timeout_minutes: Optional[int] = None
    max_failed_login_attempts: Optional[int] = None
    lockout_duration_minutes: Optional[int] = None
    password_min_length: Optional[int] = None
    require_special_chars: Optional[bool] = None


class UpdateOut(ORMModel):
    id: str
    version: str
    compatible_from: str
    changelog: str
    status: str
    uploaded_by: str
    created_at: datetime
    error: str = ""
    migration_id: str = ""
