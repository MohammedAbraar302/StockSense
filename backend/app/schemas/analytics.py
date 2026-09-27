from typing import List
from decimal import Decimal
from pydantic import BaseModel


class DashboardKPIs(BaseModel):
    total_products_in_stock: int = 0
    low_stock_items: int = 0
    out_of_stock_items: int = 0
    pending_receipts: int = 0
    pending_deliveries: int = 0
    internal_transfers_scheduled: int = 0
    inventory_total_value: Decimal = Decimal("0.00")
    today_sales_revenue: Decimal = Decimal("0.00")


class StockMovementTrendItem(BaseModel):
    date: str
    inflow: int = 0
    outflow: int = 0


class WarehouseComparisonItem(BaseModel):
    warehouse_id: str
    warehouse_name: str
    total_quantity: int = 0
    total_value: Decimal = Decimal("0.00")
    product_count: int = 0


class TopMovingProduct(BaseModel):
    product_id: str
    sku: str
    name: str
    category_name: str = "General"
    units_moved: int = 0
    revenue: Decimal = Decimal("0.00")


class SalesAnalyticsResponse(BaseModel):
    total_revenue: Decimal = Decimal("0.00")
    units_sold: int = 0
    avg_order_value: Decimal = Decimal("0.00")
    inventory_turnover_ratio: float = 0.0
    stock_velocity: str = "Optimal"
    days_of_stock_remaining: int = 45
    top_products: List[TopMovingProduct] = []
    slow_moving_products: List[TopMovingProduct] = []
