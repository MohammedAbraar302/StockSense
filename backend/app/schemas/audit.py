from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class AuditLogResponse(BaseModel):
    id: str
    user_name: Optional[str] = "System"
    action: str
    entity: str
    entity_id: Optional[str] = None
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: str
    notification_type: str
    title: str
    message: str
    is_read: bool
    link: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class StaffCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    mobile: str = Field(..., min_length=10)
    password: str = Field(..., min_length=8)
    role_name: str = "WAREHOUSE_STAFF"  # ADMIN, INVENTORY_MANAGER, WAREHOUSE_STAFF


class StaffResponse(BaseModel):
    id: str
    full_name: str
    email: str
    mobile: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
