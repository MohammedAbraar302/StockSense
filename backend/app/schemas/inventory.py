from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class StockPositionResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    sku: str
    category_name: Optional[str] = None
    warehouse_id: str
    warehouse_name: str
    location_id: str
    location_name: str
    bin_id: Optional[str] = None
    bin_name: Optional[str] = None
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    quantity_damaged: int
    unit_of_measure: str
    cost_price: Decimal
    total_valuation: Decimal

    model_config = {"from_attributes": True}


class LedgerMovementResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    sku: str
    warehouse_id: str
    warehouse_name: str
    location_id: str
    location_name: str
    bin_id: Optional[str] = None
    bin_name: Optional[str] = None
    operation_type: str
    reference_type: str
    reference_id: Optional[str] = None
    quantity_before: int
    quantity_change: int
    quantity_after: int
    user_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LowStockAlertResponse(BaseModel):
    product_id: str
    sku: str
    product_name: str
    category_name: Optional[str] = None
    total_on_hand: int
    total_available: int
    reorder_level: int
    reorder_quantity: int
    alert_level: str  # OUT_OF_STOCK, CRITICAL, LOW_STOCK
    unit_of_measure: str
