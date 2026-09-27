from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.inventory import (
    StockPositionResponse,
    LedgerMovementResponse,
    LowStockAlertResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.inventory_service import InventoryService
from app.services.product_service import ProductService

router = APIRouter(prefix="/inventory", tags=["Inventory & Ledger"])


@router.get("/stock", response_model=List[StockPositionResponse])
async def list_stock_positions(
    warehouse_id: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    bin_id: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Query real-time stock positions scoped by Warehouse, Location, or Bin.
    """
    stocks = await InventoryService.get_stock_positions(
        db=db,
        org_id=current_user.organization_id,
        warehouse_id=warehouse_id,
        location_id=location_id,
        bin_id=bin_id,
        category_id=category_id,
        search=search
    )
    return stocks


@router.get("/ledger", response_model=PaginatedResponse[LedgerMovementResponse])
async def list_movement_ledger(
    warehouse_id: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    bin_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    operation_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Query the append-only stock movement ledger tracking all receipts, deliveries, transfers, and adjustments.
    """
    offset = (page - 1) * page_size
    movements, total = await InventoryService.get_ledger(
        db=db,
        org_id=current_user.organization_id,
        warehouse_id=warehouse_id,
        location_id=location_id,
        bin_id=bin_id,
        product_id=product_id,
        operation_type=operation_type,
        limit=page_size,
        offset=offset
    )

    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedResponse[LedgerMovementResponse](
        items=movements,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/alerts/low-stock", response_model=List[LowStockAlertResponse])
async def get_low_stock_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch all items that are either OUT_OF_STOCK or below their reorder_level.
    """
    products = await ProductService.get_products(
        db=db,
        org_id=current_user.organization_id,
        low_stock_only=True
    )
    alerts = []
    for p in products:
        alert_level = "OUT_OF_STOCK" if p["total_available"] == 0 else "LOW_STOCK"
        alerts.append(LowStockAlertResponse(
            product_id=p["id"],
            sku=p["sku"],
            product_name=p["name"],
            category_name=p["category_name"],
            total_on_hand=p["total_on_hand"],
            total_available=p["total_available"],
            reorder_level=p["reorder_level"],
            reorder_quantity=p["reorder_quantity"],
            alert_level=alert_level,
            unit_of_measure=p["unit_of_measure"]
        ))
    return alerts
