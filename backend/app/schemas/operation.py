from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# --- Suppliers & Customers ---
class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class SupplierResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class CustomerResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Receipts ---
class ReceiptItemCreate(BaseModel):
    product_id: str
    location_id: str
    bin_id: Optional[str] = None
    quantity_expected: int = Field(..., ge=1)
    quantity_received: int = Field(..., ge=1)
    unit_cost: Decimal = Decimal("0.00")


class ReceiptItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: Optional[str] = None
    sku: Optional[str] = None
    location_id: str
    location_name: Optional[str] = None
    bin_id: Optional[str] = None
    bin_name: Optional[str] = None
    quantity_expected: int
    quantity_received: int
    unit_cost: Decimal

    model_config = {"from_attributes": True}


class ReceiptCreate(BaseModel):
    supplier_id: Optional[str] = None
    warehouse_id: str
    notes: Optional[str] = None
    items: List[ReceiptItemCreate] = Field(..., min_length=1)


class ReceiptResponse(BaseModel):
    id: str
    receipt_number: str
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    warehouse_id: str
    warehouse_name: Optional[str] = None
    status: str  # DRAFT, WAITING, READY, DONE, CANCELED
    notes: Optional[str] = None
    created_by_name: Optional[str] = None
    validated_by_name: Optional[str] = None
    validated_at: Optional[datetime] = None
    items: List[ReceiptItemResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Deliveries ---
class DeliveryItemCreate(BaseModel):
    product_id: str
    location_id: str
    bin_id: Optional[str] = None
    quantity_requested: int = Field(..., ge=1)
    unit_price: Decimal = Decimal("0.00")


class DeliveryItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: Optional[str] = None
    sku: Optional[str] = None
    location_id: str
    location_name: Optional[str] = None
    bin_id: Optional[str] = None
    bin_name: Optional[str] = None
    quantity_requested: int
    quantity_picked: int
    quantity_packed: int
    unit_price: Decimal

    model_config = {"from_attributes": True}


class DeliveryCreate(BaseModel):
    customer_id: Optional[str] = None
    warehouse_id: str
    notes: Optional[str] = None
    items: List[DeliveryItemCreate] = Field(..., min_length=1)


class DeliveryResponse(BaseModel):
    id: str
    delivery_number: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    warehouse_id: str
    warehouse_name: Optional[str] = None
    status: str  # DRAFT, WAITING, PICKED, PACKED, DONE, CANCELED
    notes: Optional[str] = None
    created_by_name: Optional[str] = None
    validated_by_name: Optional[str] = None
    validated_at: Optional[datetime] = None
    items: List[DeliveryItemResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Transfers ---
class TransferItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)


class TransferItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: Optional[str] = None
    sku: Optional[str] = None
    quantity: int

    model_config = {"from_attributes": True}


class TransferCreate(BaseModel):
    source_warehouse_id: str
    source_location_id: str
    source_bin_id: Optional[str] = None
    dest_warehouse_id: str
    dest_location_id: str
    dest_bin_id: Optional[str] = None
    notes: Optional[str] = None
    items: List[TransferItemCreate] = Field(..., min_length=1)


class TransferResponse(BaseModel):
    id: str
    transfer_number: str
    source_warehouse_id: str
    source_warehouse_name: Optional[str] = None
    source_location_id: str
    source_location_name: Optional[str] = None
    source_bin_id: Optional[str] = None
    source_bin_name: Optional[str] = None
    dest_warehouse_id: str
    dest_warehouse_name: Optional[str] = None
    dest_location_id: str
    dest_location_name: Optional[str] = None
    dest_bin_id: Optional[str] = None
    dest_bin_name: Optional[str] = None
    status: str  # DRAFT, APPROVED, DONE, CANCELED
    notes: Optional[str] = None
    created_by_name: Optional[str] = None
    completed_by_name: Optional[str] = None
    completed_at: Optional[datetime] = None
    items: List[TransferItemResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Adjustments ---
class AdjustmentItemCreate(BaseModel):
    product_id: str
    physical_quantity: int = Field(..., ge=0)
    reason: Optional[str] = None


class AdjustmentItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: Optional[str] = None
    sku: Optional[str] = None
    recorded_quantity: int
    physical_quantity: int
    difference: int
    reason: Optional[str] = None

    model_config = {"from_attributes": True}


class AdjustmentCreate(BaseModel):
    warehouse_id: str
    location_id: str
    bin_id: Optional[str] = None
    reason: str = Field(..., description="DAMAGE, LOSS, FOUND, COUNT_CORRECTION, OTHER")
    notes: Optional[str] = None
    items: List[AdjustmentItemCreate] = Field(..., min_length=1)


class AdjustmentResponse(BaseModel):
    id: str
    adjustment_number: str
    warehouse_id: str
    warehouse_name: Optional[str] = None
    location_id: str
    location_name: Optional[str] = None
    bin_id: Optional[str] = None
    bin_name: Optional[str] = None
    status: str
    reason: str
    notes: Optional[str] = None
    created_by_name: Optional[str] = None
    items: List[AdjustmentItemResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
