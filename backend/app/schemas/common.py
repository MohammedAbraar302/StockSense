from typing import Generic, TypeVar, List, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")


class APIErrorDetails(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class APIErrorResponse(BaseModel):
    error: APIErrorDetails


class MessageResponse(BaseModel):
    message: str
    success: bool = True
    data: Optional[Any] = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
