from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = None
    description: Optional[str] = None


class CategoryResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=100)
    category_id: Optional[str] = None
    unit_of_measure: str = "Units"
    description: Optional[str] = None
    cost_price: Decimal = Decimal("0.00")
    selling_price: Decimal = Decimal("0.00")
    reorder_level: int = 10
    reorder_quantity: int = 50
    # Optional initial stock provisioning
    initial_stock: Optional[int] = None
    initial_warehouse_id: Optional[str] = None
    initial_location_id: Optional[str] = None
    initial_bin_id: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[str] = None
    unit_of_measure: Optional[str] = None
    description: Optional[str] = None
    cost_price: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    reorder_level: Optional[int] = None
    reorder_quantity: Optional[int] = None
    status: Optional[str] = None


class ProductResponse(BaseModel):
    id: str
    organization_id: str
    sku: str
    name: str
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    unit_of_measure: str
    description: Optional[str] = None
    cost_price: Decimal
    selling_price: Decimal
    reorder_level: int
    reorder_quantity: int
    status: str
    total_on_hand: int = 0
    total_available: int = 0
    total_reserved: int = 0
    stock_status: str = "IN_STOCK"  # IN_STOCK, LOW_STOCK, OUT_OF_STOCK
    created_at: datetime

    model_config = {"from_attributes": True}


class StockByLocationItem(BaseModel):
    warehouse_id: str
    warehouse_name: str
    location_id: str
    location_name: str
    bin_id: Optional[str] = None
    bin_name: Optional[str] = None
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int


class ProductDetailResponse(BaseModel):
    product: ProductResponse
    stock_locations: List[StockByLocationItem] = []
    recent_movements: List[dict] = []
