from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def new_id() -> str:
    return str(uuid.uuid4())


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    manager_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    max_file_size_bytes: Mapped[int] = mapped_column(Integer, default=52_428_800)
    allowed_extensions: Mapped[list[str]] = mapped_column(JSON, default=list)
    default_classification: Mapped[str] = mapped_column(String(32), default="internal")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    users: Mapped[list["User"]] = relationship(back_populates="group")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    group_id: Mapped[Optional[str]] = mapped_column(ForeignKey("groups.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    group: Mapped[Optional[Group]] = relationship(back_populates="users")
    sessions: Mapped[list["Session"]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    csrf_secret: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(512), default="")
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class FileObject(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    original_name: Mapped[str] = mapped_column(String(300), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    storage_relpath: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str] = mapped_column(String(200), default="")
    group_id: Mapped[Optional[str]] = mapped_column(ForeignKey("groups.id"), nullable=True)
    uploader_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(200), default="application/octet-stream")
    detected_mime: Mapped[str] = mapped_column(String(200), default="application/octet-stream")
    extension: Mapped[str] = mapped_column(String(16), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), default="internal")
    scan_status: Mapped[str] = mapped_column(String(32), default="scanning", index=True)
    quarantine_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(32), default="v1.0")
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    parent_file_id: Mapped[Optional[str]] = mapped_column(ForeignKey("files.id"), nullable=True)
    is_current_version: Mapped[bool] = mapped_column(Boolean, default=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    permissions: Mapped[list["FilePermission"]] = relationship(
        back_populates="file", cascade="all, delete-orphan"
    )


class FilePermission(Base):
    __tablename__ = "file_permissions"
    __table_args__ = (
        UniqueConstraint("file_id", "target_type", "target_id", name="uq_file_perm_target"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_id: Mapped[str] = mapped_column(String(80), nullable=False)
    can_view: Mapped[bool] = mapped_column(Boolean, default=True)
    can_download: Mapped[bool] = mapped_column(Boolean, default=False)
    can_upload: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage: Mapped[bool] = mapped_column(Boolean, default=False)
    granted_by: Mapped[str] = mapped_column(String(36), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    file: Mapped[FileObject] = relationship(back_populates="permissions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(80), default="")
    user_role: Mapped[str] = mapped_column(String(32), default="")
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action_title: Mapped[str] = mapped_column(String(200), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), default="")
    target_id: Mapped[str] = mapped_column(String(80), default="")
    target_resource: Mapped[str] = mapped_column(String(400), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(512), default="")
    severity: Mapped[str] = mapped_column(String(16), default="info")


class SecurityPolicy(Base):
    __tablename__ = "security_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    allowed_extensions: Mapped[list[str]] = mapped_column(JSON, default=list)
    max_file_size_bytes: Mapped[int] = mapped_column(Integer, default=52_428_800)
    clamav_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    quarantine_dangerous_files: Mapped[bool] = mapped_column(Boolean, default=True)
    session_timeout_minutes: Mapped[int] = mapped_column(Integer, default=30)
    max_failed_login_attempts: Mapped[int] = mapped_column(Integer, default=5)
    lockout_duration_minutes: Mapped[int] = mapped_column(Integer, default=15)
    password_min_length: Mapped[int] = mapped_column(Integer, default=12)
    require_special_chars: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RecoveryToken(Base):
    __tablename__ = "recovery_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)


class SystemUpdate(Base):
    __tablename__ = "system_updates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    compatible_from: Mapped[str] = mapped_column(String(64), default="")
    changelog: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="uploaded", index=True)
    bundle_sha256: Mapped[str] = mapped_column(String(64), default="")
    staging_name: Mapped[str] = mapped_column(String(200), default="")
    uploaded_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    rollback_result: Mapped[str] = mapped_column(Text, default="")
    migration_id: Mapped[str] = mapped_column(String(120), default="")
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class MaintenanceState(Base):
    __tablename__ = "maintenance_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str] = mapped_column(String(300), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProcessedBackup(Base):
    __tablename__ = "backup_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    path_name: Mapped[str] = mapped_column(String(300), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    encrypted: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(36), default="system")
    notes: Mapped[str] = mapped_column(Text, default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


@event.listens_for(AuditLog, "before_update")
def _reject_audit_update(mapper, connection, target):  # noqa: ARG001
    raise RuntimeError("audit logs are append-only")


@event.listens_for(AuditLog, "before_delete")
def _reject_audit_delete(mapper, connection, target):  # noqa: ARG001
    raise RuntimeError("audit logs are append-only")
