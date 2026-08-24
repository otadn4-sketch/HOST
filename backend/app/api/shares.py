from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.entities import User
from app.services.phases import require_phase

router = APIRouter(prefix="/api/shares", tags=["shares"])


@router.get("")
def list_shares(_user: User = Depends(get_current_user)):
    require_phase("phase_4_sharing_enabled", "فاز ۴ (اشتراک‌گذاری امن و RBAC دانه‌ای) هنوز فعال نشده است.")
    raise HTTPException(status_code=501, detail="پیوند اشتراک‌گذاری در این نسخه فعال نیست.")


@router.post("")
def create_share(_user: User = Depends(get_current_user)):
    require_phase("phase_4_sharing_enabled", "فاز ۴ (اشتراک‌گذاری امن و RBAC دانه‌ای) هنوز فعال نشده است.")
    raise HTTPException(status_code=501, detail="ایجاد پیوند اشتراک‌گذاری تا تکمیل کنترل دسترسی دانه‌ای غیرفعال است.")
