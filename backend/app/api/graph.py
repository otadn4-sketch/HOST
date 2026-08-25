from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_db, require_system_admin
from app.models.entities import User
from app.services.graph import build_relationship_graph
from app.services.phases import is_loopback_request, require_phase

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/relationships")
def relationship_graph(
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_system_admin),
):
    require_phase("phase_5_security_graph_enabled", "فاز ۵ (گراف تعاملات محلی) فعال نیست.")
    if not is_loopback_request(request):
        raise HTTPException(
            status_code=403,
            detail="گراف تعاملات فقط روی localhost در دسترس است و روی محیط production عمومی فعال نیست.",
        )
    return {"graph": build_relationship_graph(db)}
