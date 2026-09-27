import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from app.core.database import Base


def generate_uuid() -> str:
    """Generate a clean UUID hex string."""
    return str(uuid.uuid4())


class TimestampMixin:
    """Standard timestamp mixin with UTC timezone."""
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
