from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.schemas.reconciliation import (
    EODPreviewResponse,
    EODCloseRequest,
    EODClosingResponse,
)
from app.services.reconciliation_service import ReconciliationService

router = APIRouter(prefix="/reconciliation", tags=["End-of-Day Reconciliation"])


@router.get("/preview", response_model=EODPreviewResponse)
async def preview_eod_reconciliation(
    warehouse_id: str = Query(...),
    location_id: str = Query(...),
    target_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compute real-time mathematical breakdown for End-of-Day reconciliation:
    Opening Stock + Receipts - Deliveries + Transfers In - Transfers Out ± Adjustments = Expected Closing Stock.
    """
    preview = await ReconciliationService.get_eod_preview(
        db=db,
        warehouse_id=warehouse_id,
        location_id=location_id,
        target_date=target_date
    )
    return preview


@router.post("/close", response_model=EODClosingResponse)
async def close_end_of_day(
    req: EODCloseRequest,
    current_user: User = Depends(require_roles(["ADMIN", "INVENTORY_MANAGER"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit verified physical counts for End-of-Day reconciliation.
    Detects variance against expected stock. If variance != 0, an explanation is mandatory.
    Enforces idempotency: duplicate closing for the same location and date is prevented.
    """
    try:
        items_data = [item.model_dump() for item in req.items]
        closing = await ReconciliationService.close_eod(
            db=db,
            org_id=current_user.organization_id,
            warehouse_id=req.warehouse_id,
            location_id=req.location_id,
            items_input=items_data,
            closing_date=req.closing_date,
            notes=req.notes,
            user_id=current_user.id
        )

        history = await ReconciliationService.get_closing_history(db, current_user.organization_id, req.warehouse_id)
        target = next((c for c in history if c.id == closing.id), closing)
        return target
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/history", response_model=List[EODClosingResponse])
async def list_closing_history(
    warehouse_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve historical daily closing reports with full itemized variance breakdowns."""
    closings = await ReconciliationService.get_closing_history(
        db=db,
        org_id=current_user.organization_id,
        warehouse_id=warehouse_id
    )
    return closings
