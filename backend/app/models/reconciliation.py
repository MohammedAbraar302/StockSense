from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Date, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, date
from app.core.database import Base
from app.models.base import generate_uuid, TimestampMixin


class DailyClosing(Base, TimestampMixin):
    """
    End-of-day reconciliation record for a warehouse location.
    Enforces no accidental duplicate closings for the same location and date.
    """
    __tablename__ = "daily_closings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    location_id = Column(String(36), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    closing_date = Column(Date, default=date.today, nullable=False, index=True)
    status = Column(String(50), default="CLOSED", nullable=False)  # DRAFT, CLOSED, REOPENED
    notes = Column(Text, nullable=True)
    closed_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    warehouse = relationship("Warehouse")
    location = relationship("Location")
    closed_by = relationship("User")
    items = relationship("DailyClosingItem", back_populates="closing", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("location_id", "closing_date", name="uq_location_closing_date"),
    )


class DailyClosingItem(Base, TimestampMixin):
    """Reconciliation item details and variance breakdown."""
    __tablename__ = "daily_closing_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    daily_closing_id = Column(String(36), ForeignKey("daily_closings.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)

    opening_quantity = Column(Integer, default=0, nullable=False)
    receipts_quantity = Column(Integer, default=0, nullable=False)
    deliveries_quantity = Column(Integer, default=0, nullable=False)
    transfers_in_quantity = Column(Integer, default=0, nullable=False)
    transfers_out_quantity = Column(Integer, default=0, nullable=False)
    adjustments_quantity = Column(Integer, default=0, nullable=False)

    expected_quantity = Column(Integer, default=0, nullable=False)
    physical_quantity = Column(Integer, default=0, nullable=False)
    variance = Column(Integer, default=0, nullable=False)  # physical - expected
    explanation = Column(Text, nullable=True)

    closing = relationship("DailyClosing", back_populates="items")
    product = relationship("Product")
