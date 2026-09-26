from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.analytics import (
    DashboardKPIs,
    StockMovementTrendItem,
    WarehouseComparisonItem,
    SalesAnalyticsResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Dashboard & Analytics"])


@router.get("/dashboard/kpis", response_model=DashboardKPIs)
async def get_dashboard_kpis(
    warehouse_id: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Real-time high-level KPIs aggregated across the selected location scope:
    Total products in stock, low-stock count, pending receipts/deliveries, scheduled transfers,
    total inventory valuation, and today's sales.
    """
    kpis = await AnalyticsService.get_dashboard_kpis(
        db=db,
        org_id=current_user.organization_id,
        warehouse_id=warehouse_id,
        location_id=location_id
    )
    return kpis


@router.get("/dashboard/stock-movement", response_model=List[StockMovementTrendItem])
async def get_stock_movement_trends(
    days: int = Query(7, ge=1, le=30),
    warehouse_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Time-series stock inflows vs outflows for the dashboard chart.
    """
    trend = await AnalyticsService.get_movement_trend(
        db=db,
        org_id=current_user.organization_id,
        days=days,
        warehouse_id=warehouse_id
    )
    return trend


@router.get("/dashboard/warehouse-comparison", response_model=List[WarehouseComparisonItem])
async def get_warehouse_comparison(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stock volume and valuation distribution comparison across warehouses.
    """
    comparison = await AnalyticsService.get_warehouse_comparison(
        db=db,
        org_id=current_user.organization_id
    )
    return comparison


@router.get("/sales", response_model=SalesAnalyticsResponse)
async def get_sales_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Real sales metrics: total revenue, units sold, average order value, turnover ratio, and top moving products.
    """
    sales = await AnalyticsService.get_sales_analytics(
        db=db,
        org_id=current_user.organization_id
    )
    return sales
