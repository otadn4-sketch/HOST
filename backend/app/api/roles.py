from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db
from app.models.entities import OrgRole, User
from app.schemas import OrgRoleCreateIn, OrgRolePatchIn
from app.security.rbac import can_access_admin_panel, is_admin
from app.services.audit import write_audit
from app.services.files import serialize_role

router = APIRouter(prefix="/api/roles", tags=["roles"])

ALLOWED_CUSTOM_LEVELS = {"group_admin", "user", "viewer"}


def _members_count(db: DBSession, role_id: str) -> int:
    return db.query(User).filter(User.org_role_id == role_id, User.status != "deleted").count()


@router.get("")
def list_roles(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    if not can_access_admin_panel(user):
        raise HTTPException(status_code=403, detail="دسترسی ندارید.")
    q = db.query(OrgRole).filter(OrgRole.is_active.is_(True))
    if user.role == "group_admin":
        q = q.filter(OrgRole.permission_level.in_(["group_admin", "user", "viewer"]))
    roles = q.order_by(OrgRole.is_system.desc(), OrgRole.name.asc()).all()
    return {"roles": [serialize_role(r, _members_count(db, r.id)) for r in roles]}


@router.post("")
def create_role(
    payload: OrgRoleCreateIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="فقط مدیر سامانه می‌تواند نقش جدید تعریف کند.")
    level = payload.permission_level.strip()
    if level not in ALLOWED_CUSTOM_LEVELS:
        raise HTTPException(status_code=400, detail="سطح دسترسی نقش سفارشی باید مدیر گروه، کاربر یا مشاهده‌گر باشد.")
    code = payload.code.strip().upper().replace(" ", "-")
    if db.query(OrgRole).filter(OrgRole.code == code).one_or_none():
        raise HTTPException(status_code=409, detail="کد نقش تکراری است.")
    role = OrgRole(
        name=payload.name.strip(),
        code=code,
        description=payload.description.strip(),
        permission_level=level,
        is_system=False,
        is_active=True,
    )
    db.add(role)
    db.flush()
    write_audit(
        db,
        user=user,
        action="role_updated",
        target_resource=role.name,
        target_type="role",
        target_id=role.id,
        details="ایجاد نقش سازمانی",
        request=request,
    )
    return {"role": serialize_role(role, 0)}


@router.patch("/{role_id}")
def patch_role(
    role_id: str,
    payload: OrgRolePatchIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="فقط مدیر سامانه می‌تواند نقش را ویرایش کند.")
    role = db.query(OrgRole).filter(OrgRole.id == role_id).one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="نقش یافت نشد.")
    if payload.name:
        role.name = payload.name.strip()
    if payload.description is not None:
        role.description = payload.description.strip()
    if payload.code and not role.is_system:
        code = payload.code.strip().upper().replace(" ", "-")
        clash = db.query(OrgRole).filter(OrgRole.code == code, OrgRole.id != role.id).one_or_none()
        if clash:
            raise HTTPException(status_code=409, detail="کد نقش تکراری است.")
        role.code = code
    if payload.permission_level and not role.is_system:
        if payload.permission_level not in ALLOWED_CUSTOM_LEVELS:
            raise HTTPException(status_code=400, detail="سطح دسترسی نامعتبر است.")
        role.permission_level = payload.permission_level
        for member in db.query(User).filter(User.org_role_id == role.id).all():
            member.role = role.permission_level
    if payload.is_active is not None and not role.is_system:
        role.is_active = payload.is_active
    write_audit(
        db,
        user=user,
        action="role_updated",
        target_resource=role.name,
        target_type="role",
        target_id=role.id,
        details="ویرایش نقش سازمانی",
        request=request,
    )
    return {"role": serialize_role(role, _members_count(db, role.id))}


@router.delete("/{role_id}")
def delete_role(
    role_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="فقط مدیر سامانه می‌تواند نقش را حذف کند.")
    role = db.query(OrgRole).filter(OrgRole.id == role_id).one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="نقش یافت نشد.")
    if role.is_system:
        raise HTTPException(status_code=400, detail="نقش‌های سیستمی قابل حذف نیستند.")
    fallback = (
        db.query(OrgRole)
        .filter(OrgRole.is_system.is_(True), OrgRole.permission_level == role.permission_level)
        .one_or_none()
    )
    for member in db.query(User).filter(User.org_role_id == role.id).all():
        member.org_role_id = fallback.id if fallback else None
        member.role = role.permission_level
    write_audit(
        db,
        user=user,
        action="role_updated",
        target_resource=role.name,
        target_type="role",
        target_id=role.id,
        details="حذف نقش سازمانی",
        severity="warning",
        request=request,
    )
    db.delete(role)
    return {"ok": True}
