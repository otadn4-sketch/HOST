from __future__ import annotations

from app.models.entities import Group, MaintenanceState, User
from app.security.constants import DEFAULT_ALLOWED_EXTENSIONS
from app.security.passwords import hash_password
from app.services.policy import get_or_create_policy


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


def bootstrap_schema(db) -> None:
    get_or_create_policy(db)
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
