from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.models.base import generate_uuid, TimestampMixin


class AuditLog(Base):
    """Immutable audit trail for all business-critical operations."""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity = Column(String(100), nullable=False, index=True)  # PRODUCT, RECEIPT, DELIVERY, TRANSFER, ADJUSTMENT, etc.
    entity_id = Column(String(100), nullable=True, index=True)
    before_state = Column(Text, nullable=True)  # Serialized JSON
    after_state = Column(Text, nullable=True)   # Serialized JSON
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    user = relationship("User")


class Notification(Base, TimestampMixin):
    """System notifications for low stock, pending operations, and EOD alerts."""
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    notification_type = Column(String(50), nullable=False, index=True)
    # LOW_STOCK, OUT_OF_STOCK, PENDING_RECEIPT, PENDING_DELIVERY, TRANSFER_PENDING, STOCK_VARIANCE, EOD_PENDING
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    link = Column(String(255), nullable=True)

    user = relationship("User")
