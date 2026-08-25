from __future__ import annotations

from dataclasses import dataclass

from app.models.entities import FileObject, FilePermission, User

ROLES = ("system_admin", "group_admin", "user", "viewer")


@dataclass
class FileAccess:
    can_view: bool = False
    can_download: bool = False
    can_upload: bool = False
    can_manage: bool = False


def is_admin(user: User) -> bool:
    return user.role == "system_admin"


def is_group_admin(user: User) -> bool:
    return user.role == "group_admin"


def can_access_admin_panel(user: User) -> bool:
    return user.role in {"system_admin", "group_admin"}


def can_see_dashboard(user: User) -> bool:
    return user.role == "system_admin"


def can_manage_users(user: User, target: User | None = None) -> bool:
    if user.role == "system_admin":
        return True
    if user.role == "group_admin" and target is not None:
        return target.group_id == user.group_id and target.role in {"user", "viewer"}
    return False


def can_create_user_with_role(actor: User, role: str) -> bool:
    if role not in ROLES:
        return False
    if actor.role == "system_admin":
        return True
    if actor.role == "group_admin":
        return role in {"user", "viewer"}
    return False


def can_manage_group(actor: User, group_id: str | None) -> bool:
    if actor.role == "system_admin":
        return True
    if actor.role == "group_admin":
        return actor.group_id == group_id
    return False


def can_upload(user: User) -> bool:
    if user.status != "active":
        return False
    return user.role in {"system_admin", "group_admin", "user"}


def evaluate_file_access(user: User, file: FileObject, permissions: list[FilePermission]) -> FileAccess:
    access = FileAccess()
    if file.is_deleted:
        return access

    quarantined = file.scan_status in {"quarantined", "suspicious", "scanning", "pending"}

    if user.role == "system_admin":
        access.can_view = True
        access.can_manage = True
        access.can_upload = True
        reason = (file.quarantine_reason or "")
        malware = file.scan_status == "quarantined" and (
            "شناسایی بدافزار" in reason or "malware" in reason.lower()
        )
        unscanned = "پویش بدافزار در دسترس نبود" in reason
        access.can_download = not malware and not unscanned
        return access

    if user.id == file.uploader_id:
        access.can_view = True
        access.can_manage = True
        access.can_upload = True
        access.can_download = file.scan_status == "clean"
        # uploader still cannot download quarantined files
        return access

    if user.role == "group_admin" and file.group_id and file.group_id == user.group_id:
        access.can_view = True
        access.can_manage = True
        access.can_upload = True
        access.can_download = file.scan_status == "clean"
        return access

    if quarantined:
        return access

    if file.classification == "public":
        access.can_view = True
        access.can_download = True
    elif file.classification == "internal" and user.role in {"user", "group_admin", "system_admin"}:
        if file.group_id and file.group_id == user.group_id:
            access.can_view = True
            access.can_download = user.role != "viewer"
        elif user.role != "viewer":
            access.can_view = True
            access.can_download = False

    for perm in permissions:
        matched = False
        if perm.target_type == "user" and perm.target_id == user.id:
            matched = True
        elif perm.target_type == "role" and perm.target_id == user.role:
            matched = True
        elif perm.target_type == "group" and user.group_id and perm.target_id == user.group_id:
            matched = True
        if not matched:
            continue
        access.can_view = access.can_view or perm.can_view
        access.can_download = access.can_download or perm.can_download
        access.can_upload = access.can_upload or perm.can_upload
        access.can_manage = access.can_manage or perm.can_manage

    if file.scan_status != "clean":
        access.can_download = False

    if user.role == "viewer":
        access.can_upload = False
        access.can_manage = False
        if file.classification != "public":
            # viewer downloads only with explicit download grant
            granted = any(
                p.can_download
                and (
                    (p.target_type == "user" and p.target_id == user.id)
                    or (p.target_type == "role" and p.target_id == "viewer")
                    or (p.target_type == "group" and user.group_id and p.target_id == user.group_id)
                )
                for p in permissions
            )
            if not granted:
                access.can_download = False

    return access


def can_read_audit(user: User) -> bool:
    return user.role in {"system_admin", "group_admin"}


def can_manage_policy(user: User) -> bool:
    return user.role == "system_admin"


def can_manage_updates(user: User) -> bool:
    return user.role == "system_admin"
