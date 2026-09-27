from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class StorageBinCreate(BaseModel):
    location_id: str
    rack: str = Field(..., min_length=1, max_length=50)
    bin_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    max_capacity: int = 1000


class StorageBinResponse(BaseModel):
    id: str
    location_id: str
    rack: str
    bin_code: str
    name: str
    max_capacity: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LocationCreate(BaseModel):
    warehouse_id: str
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    location_type: str = "STORAGE"  # STORAGE, PRODUCTION, SCRAP, TRANSIT


class LocationResponse(BaseModel):
    id: str
    warehouse_id: str
    code: str
    name: str
    location_type: str
    is_active: bool
    bins: List[StorageBinResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class WarehouseCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = None
    contact_person: Optional[str] = None


class WarehouseResponse(BaseModel):
    id: str
    organization_id: str
    code: str
    name: str
    address: Optional[str] = None
    contact_person: Optional[str] = None
    is_active: bool
    locations: List[LocationResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class TreeBinItem(BaseModel):
    id: str
    rack: str
    bin_code: str
    name: str


class TreeLocationItem(BaseModel):
    id: str
    code: str
    name: str
    location_type: str
    bins: List[TreeBinItem] = []


class TreeWarehouseItem(BaseModel):
    id: str
    code: str
    name: str
    locations: List[TreeLocationItem] = []


class GlobalLocationTreeResponse(BaseModel):
    warehouses: List[TreeWarehouseItem] = []
