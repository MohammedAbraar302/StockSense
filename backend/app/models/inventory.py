from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, UniqueConstraint, CheckConstraint, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.models.base import generate_uuid, TimestampMixin


class Inventory(Base, TimestampMixin):
    """
    Inventory Position represents the current physical stock aggregate of a
    Product at a specific Warehouse, Location, and Storage Bin.
    """
    __tablename__ = "inventory"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id = Column(String(36), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True)
    bin_id = Column(String(36), ForeignKey("storage_bins.id", ondelete="SET NULL"), nullable=True, index=True)

    quantity_on_hand = Column(Integer, default=0, nullable=False)
    quantity_reserved = Column(Integer, default=0, nullable=False)
    quantity_damaged = Column(Integer, default=0, nullable=False)

    product = relationship("Product", back_populates="inventory_positions")
    warehouse = relationship("Warehouse")
    location = relationship("Location")
    bin = relationship("StorageBin")

    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", "location_id", "bin_id", name="uq_inventory_position"),
        CheckConstraint("quantity_on_hand >= 0", name="chk_non_negative_on_hand"),
        CheckConstraint("quantity_reserved >= 0", name="chk_non_negative_reserved"),
        CheckConstraint("quantity_damaged >= 0", name="chk_non_negative_damaged"),
    )

    @property
    def quantity_available(self) -> int:
        """Derived available stock: on_hand - reserved."""
        return max(0, (self.quantity_on_hand or 0) - (self.quantity_reserved or 0))


class InventoryMovement(Base):
    """
    Immutable, append-only Inventory Ledger.
    Every inventory-changing transaction MUST create a ledger record here.
    """
    __tablename__ = "inventory_movements"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)
    location_id = Column(String(36), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True)
    bin_id = Column(String(36), ForeignKey("storage_bins.id", ondelete="SET NULL"), nullable=True, index=True)

    operation_type = Column(String(50), nullable=False, index=True)
    # RECEIPT, DELIVERY, TRANSFER_OUT, TRANSFER_IN, ADJUSTMENT, DAMAGE, RETURN, INITIAL_STOCK

    reference_type = Column(String(50), nullable=False)  # RECEIPT, DELIVERY, TRANSFER, ADJUSTMENT, EOD, MANUAL
    reference_id = Column(String(100), nullable=True, index=True)

    quantity_before = Column(Integer, nullable=False)
    quantity_change = Column(Integer, nullable=False)  # positive for increase, negative for decrease
    quantity_after = Column(Integer, nullable=False)

    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    product = relationship("Product")
    warehouse = relationship("Warehouse")
    location = relationship("Location")
    bin = relationship("StorageBin")
    user = relationship("User")
