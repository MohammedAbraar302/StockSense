from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field


class EODCalculationRow(BaseModel):
    product_id: str
    product_name: str
    sku: str
    unit_of_measure: str
    opening_stock: int
    receipts: int
    deliveries: int
    transfers_in: int
    transfers_out: int
    adjustments: int
    expected_stock: int
    current_system_stock: int


class EODPreviewResponse(BaseModel):
    warehouse_id: str
    warehouse_name: str
    location_id: str
    location_name: str
    target_date: date
    is_already_closed: bool
    existing_closing_id: Optional[str] = None
    items: List[EODCalculationRow] = []


class EODCloseItemInput(BaseModel):
    product_id: str
    physical_quantity: int = Field(..., ge=0)
    explanation: Optional[str] = None


class EODCloseRequest(BaseModel):
    warehouse_id: str
    location_id: str
    closing_date: Optional[date] = None
    notes: Optional[str] = None
    items: List[EODCloseItemInput] = Field(..., min_length=1)


class EODClosingItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    sku: str
    unit_of_measure: str
    opening_quantity: int
    receipts_quantity: int
    deliveries_quantity: int
    transfers_in_quantity: int
    transfers_out_quantity: int
    adjustments_quantity: int
    expected_quantity: int
    physical_quantity: int
    variance: int
    explanation: Optional[str] = None

    model_config = {"from_attributes": True}


class EODClosingResponse(BaseModel):
    id: str
    warehouse_id: str
    warehouse_name: str
    location_id: str
    location_name: str
    closing_date: date
    status: str
    notes: Optional[str] = None
    closed_by_name: Optional[str] = None
    closed_at: datetime
    items: List[EODClosingItemResponse] = []

    model_config = {"from_attributes": True}
