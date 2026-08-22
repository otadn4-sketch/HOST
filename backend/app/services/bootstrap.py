from __future__ import annotations

from app.models.entities import Group, MaintenanceState, OrgRole, User
from app.security.constants import DEFAULT_ALLOWED_EXTENSIONS
from app.security.passwords import hash_password
from app.services.ai_prompts import SYSTEM_ORG_ROLES
from app.services.policy import ensure_runtime_schema, get_or_create_ai_settings, get_or_create_policy


DEFAULT_GROUPS = [
    {
        "code": "SEC-IT",
        "name": "فناوری اطلاعات و امنیت",
        "description": "مدیریت زیرساخت، کنترل دسترسی و امنیت",
        "max_file_size_bytes": 50 * 1024 * 1024,
        "default_classification": "confidential",
    },
    {
        "code": "FIN-ACC",
        "name": "مالی و بودجه",
        "description": "گزارش‌های مالی و بودجه",
        "max_file_size_bytes": 25 * 1024 * 1024,
        "default_classification": "confidential",
    },
    {
        "code": "OPS-NET",
        "name": "عملیات و زیرساخت شبکه",
        "description": "عملیات شبکه و سرور",
        "max_file_size_bytes": 40 * 1024 * 1024,
        "default_classification": "internal",
    },
    {
        "code": "HR-ADM",
        "name": "منابع انسانی و اداری",
        "description": "اسناد اداری و منابع انسانی",
        "max_file_size_bytes": 20 * 1024 * 1024,
        "default_classification": "internal",
    },
    {
        "code": "LEGAL-AUD",
        "name": "نظارت و بازرسی",
        "description": "بازرسی و انطباق",
        "max_file_size_bytes": 15 * 1024 * 1024,
        "default_classification": "secret",
    },
]


def _seed_org_roles(db) -> None:
    for item in SYSTEM_ORG_ROLES:
        existing = db.query(OrgRole).filter(OrgRole.code == item["code"]).one_or_none()
        if existing is None:
            db.add(
                OrgRole(
                    code=item["code"],
                    name=item["name"],
                    description=item["description"],
                    permission_level=item["permission_level"],
                    is_system=True,
                    is_active=True,
                )
            )
        else:
            existing.is_system = True
            if not existing.name:
                existing.name = item["name"]
    db.flush()
    users = db.query(User).filter(User.org_role_id.is_(None)).all()
    if users:
        by_level = {r.permission_level: r for r in db.query(OrgRole).filter(OrgRole.is_system.is_(True)).all()}
        for user in users:
            role_row = by_level.get(user.role)
            if role_row:
                user.org_role_id = role_row.id
        db.flush()


def bootstrap_schema(db) -> None:
    ensure_runtime_schema(db)
    get_or_create_policy(db)
    get_or_create_ai_settings(db)
    _seed_org_roles(db)
    if db.query(MaintenanceState).filter(MaintenanceState.id == 1).one_or_none() is None:
        db.add(MaintenanceState(id=1, enabled=False))
    if db.query(Group).count() == 0:
        for item in DEFAULT_GROUPS:
            db.add(
                Group(
                    name=item["name"],
                    code=item["code"],
                    description=item["description"],
                    max_file_size_bytes=item["max_file_size_bytes"],
                    allowed_extensions=list(DEFAULT_ALLOWED_EXTENSIONS),
                    default_classification=item["default_classification"],
                )
            )
    db.flush()


def seed_dev_users(db, settings) -> None:
    if not settings.eytan_seed_dev:
        return
    mapping = [
        ("admin", "مدیر سامانه", "system_admin", "SEC-IT", settings.dev_admin_password),
        ("groupadmin", "مدیر گروه", "group_admin", "FIN-ACC", settings.dev_group_admin_password),
        ("user", "کاربر سازمانی", "user", "OPS-NET", settings.dev_user_password),
        ("viewer", "مشاهده‌گر", "viewer", "LEGAL-AUD", settings.dev_viewer_password),
    ]
    for username, full_name, role, code, password in mapping:
        if not password:
            continue
        if db.query(User).filter(User.username == username).one_or_none():
            continue
        group = db.query(Group).filter(Group.code == code).one_or_none()
        db.add(
            User(
                username=username,
                full_name=full_name,
                email=f"{username}@eytan.local",
                password_hash=hash_password(password),
                role=role,
                group_id=group.id if group else None,
                status="active",
                must_change_password=True,
            )
        )
    db.flush()
