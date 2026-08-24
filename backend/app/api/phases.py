from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.entities import User
from app.services.phases import phase_status

router = APIRouter(prefix="/api/phases", tags=["phases"])


@router.get("")
def get_phases(_user: User = Depends(get_current_user)):
    return phase_status()
