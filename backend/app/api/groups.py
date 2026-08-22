from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_db
from app.models.entities import FileObject, Group, User
from app.schemas import GroupCreateIn, GroupPatchIn
from app.security.rbac import can_manage_group, is_admin
from app.services.audit import write_audit
from app.services.files import serialize_group

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("")
def list_groups(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Group).filter(Group.is_active.is_(True))
    if user.role == "group_admin":
        q = db.query(Group).filter(Group.id == user.group_id)
    elif user.role in {"user", "viewer"}:
        q = db.query(Group).filter(Group.id == user.group_id)
    groups = q.order_by(Group.name.asc()).all()
    result = []
    for g in groups:
        count = db.query(User).filter(User.group_id == g.id).count()
        manager = db.query(User).filter(User.id == g.manager_id).one_or_none() if g.manager_id else None
        result.append(serialize_group(g, count, manager.full_name if manager else ""))
    return {"groups": result}


@router.get("/{group_id}")
def get_group(group_id: str, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.query(Group).filter(Group.id == group_id).one_or_none()
    if group is None:
        raise HTTPException(status_code=404, detail="گروه یافت نشد.")
    if not is_admin(user) and user.group_id != group.id:
        raise HTTPException(status_code=404, detail="گروه یافت نشد.")
    count = db.query(User).filter(User.group_id == group.id).count()
    manager = db.query(User).filter(User.id == group.manager_id).one_or_none() if group.manager_id else None
    return {"group": serialize_group(group, count, manager.full_name if manager else "")}


@router.post("")
def create_group(
    payload: GroupCreateIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="فقط مدیر سامانه می‌تواند گروه ایجاد کند.")
    if db.query(Group).filter(Group.code == payload.code).one_or_none():
        raise HTTPException(status_code=409, detail="کد گروه تکراری است.")
    group = Group(
        name=payload.name.strip(),
        code=payload.code.strip().upper(),
        description=payload.description,
        manager_id=payload.manager_id,
        max_file_size_bytes=max(1, payload.max_file_size_mb) * 1024 * 1024,
        allowed_extensions=payload.allowed_file_extensions,
        default_classification=payload.default_classification,
    )
    db.add(group)
    db.flush()
    write_audit(db, user=user, action="group_updated", target_resource=group.name, target_type="group", target_id=group.id, details="ایجاد گروه", request=request)
    return {"group": serialize_group(group, 0)}


@router.patch("/{group_id}")
def patch_group(
    group_id: str,
    payload: GroupPatchIn,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    group = db.query(Group).filter(Group.id == group_id).one_or_none()
    if group is None or not can_manage_group(user, group.id):
        raise HTTPException(status_code=404, detail="گروه یافت نشد.")
    if payload.name:
        group.name = payload.name
    if payload.code:
        code = payload.code.strip().upper()
        clash = db.query(Group).filter(Group.code == code, Group.id != group.id).one_or_none()
        if clash:
            raise HTTPException(status_code=409, detail="کد گروه تکراری است.")
        group.code = code
    if payload.description is not None:
        group.description = payload.description
    if payload.manager_id is not None and is_admin(user):
        group.manager_id = payload.manager_id
    if payload.max_file_size_mb:
        group.max_file_size_bytes = payload.max_file_size_mb * 1024 * 1024
    if payload.allowed_file_extensions is not None:
        group.allowed_extensions = payload.allowed_file_extensions
    if payload.default_classification:
        group.default_classification = payload.default_classification
    if payload.is_active is not None and is_admin(user):
        group.is_active = payload.is_active
    write_audit(db, user=user, action="group_updated", target_resource=group.name, target_type="group", target_id=group.id, details="ویرایش گروه", request=request)
    count = db.query(User).filter(User.group_id == group.id).count()
    return {"group": serialize_group(group, count)}


@router.delete("/{group_id}")
def delete_group(
    group_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="فقط مدیر سامانه می‌تواند واحد را حذف کند.")
    group = db.query(Group).filter(Group.id == group_id).one_or_none()
    if group is None:
        raise HTTPException(status_code=404, detail="گروه یافت نشد.")
    members = db.query(User).filter(User.group_id == group.id, User.status != "deleted").count()
    files = db.query(FileObject).filter(FileObject.group_id == group.id, FileObject.is_deleted.is_(False)).count()
    if members or files:
        raise HTTPException(
            status_code=409,
            detail="ابتدا کاربران و فایل‌های این واحد را منتقل یا حذف کنید.",
        )
    group.is_active = False
    write_audit(
        db,
        user=user,
        action="group_deleted",
        target_resource=group.name,
        target_type="group",
        target_id=group.id,
        details="حذف واحد سازمانی",
        severity="warning",
        request=request,
    )
    return {"ok": True}
