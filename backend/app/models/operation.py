from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.models.base import generate_uuid, TimestampMixin


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)


class Receipt(Base, TimestampMixin):
    """Incoming stock from supplier."""
    __tablename__ = "receipts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    receipt_number = Column(String(100), unique=True, nullable=False, index=True)
    supplier_id = Column(String(36), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(50), default="DRAFT", nullable=False)  # DRAFT, WAITING, READY, DONE, CANCELED
    notes = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validated_at = Column(DateTime, nullable=True)

    supplier = relationship("Supplier")
    warehouse = relationship("Warehouse")
    created_by = relationship("User", foreign_keys=[created_by_id])
    validated_by = relationship("User", foreign_keys=[validated_by_id])
    items = relationship("ReceiptItem", back_populates="receipt", cascade="all, delete-orphan")


class ReceiptItem(Base, TimestampMixin):
    __tablename__ = "receipt_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    receipt_id = Column(String(36), ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    location_id = Column(String(36), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    bin_id = Column(String(36), ForeignKey("storage_bins.id", ondelete="SET NULL"), nullable=True)
    quantity_expected = Column(Integer, default=0, nullable=False)
    quantity_received = Column(Integer, default=0, nullable=False)
    unit_cost = Column(Numeric(12, 2), default=0.00, nullable=False)

    receipt = relationship("Receipt", back_populates="items")
    product = relationship("Product")
    location = relationship("Location")
    bin = relationship("StorageBin")


class Delivery(Base, TimestampMixin):
    """Outgoing stock to customer."""
    __tablename__ = "deliveries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    delivery_number = Column(String(100), unique=True, nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(50), default="DRAFT", nullable=False)  # DRAFT, WAITING, PICKED, PACKED, DONE, CANCELED
    notes = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validated_at = Column(DateTime, nullable=True)

    customer = relationship("Customer")
    warehouse = relationship("Warehouse")
    created_by = relationship("User", foreign_keys=[created_by_id])
    validated_by = relationship("User", foreign_keys=[validated_by_id])
    items = relationship("DeliveryItem", back_populates="delivery", cascade="all, delete-orphan")


class DeliveryItem(Base, TimestampMixin):
    __tablename__ = "delivery_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    delivery_id = Column(String(36), ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    location_id = Column(String(36), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    bin_id = Column(String(36), ForeignKey("storage_bins.id", ondelete="SET NULL"), nullable=True)
    quantity_requested = Column(Integer, default=0, nullable=False)
    quantity_picked = Column(Integer, default=0, nullable=False)
    quantity_packed = Column(Integer, default=0, nullable=False)
    unit_price = Column(Numeric(12, 2), default=0.00, nullable=False)

    delivery = relationship("Delivery", back_populates="items")
    product = relationship("Product")
    location = relationship("Location")
    bin = relationship("StorageBin")


class Transfer(Base, TimestampMixin):
    """Internal stock movement between locations or warehouses."""
    __tablename__ = "transfers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    transfer_number = Column(String(100), unique=True, nullable=False, index=True)

    source_warehouse_id = Column(String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    source_location_id = Column(String(36), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    source_bin_id = Column(String(36), ForeignKey("storage_bins.id", ondelete="SET NULL"), nullable=True)

    dest_warehouse_id = Column(String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    dest_location_id = Column(String(36), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    dest_bin_id = Column(String(36), ForeignKey("storage_bins.id", ondelete="SET NULL"), nullable=True)

    status = Column(String(50), default="DRAFT", nullable=False)  # DRAFT, APPROVED, DONE, CANCELED
    notes = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at = Column(DateTime, nullable=True)

    source_warehouse = relationship("Warehouse", foreign_keys=[source_warehouse_id])
    source_location = relationship("Location", foreign_keys=[source_location_id])
    source_bin = relationship("StorageBin", foreign_keys=[source_bin_id])

    dest_warehouse = relationship("Warehouse", foreign_keys=[dest_warehouse_id])
    dest_location = relationship("Location", foreign_keys=[dest_location_id])
    dest_bin = relationship("StorageBin", foreign_keys=[dest_bin_id])

    items = relationship("TransferItem", back_populates="transfer", cascade="all, delete-orphan")


class TransferItem(Base, TimestampMixin):
    __tablename__ = "transfer_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transfer_id = Column(String(36), ForeignKey("transfers.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)

    transfer = relationship("Transfer", back_populates="items")
    product = relationship("Product")


class Adjustment(Base, TimestampMixin):
    """Stock adjustment reconciling physical count with system stock."""
    __tablename__ = "adjustments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    adjustment_number = Column(String(100), unique=True, nullable=False, index=True)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    location_id = Column(String(36), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    bin_id = Column(String(36), ForeignKey("storage_bins.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="DRAFT", nullable=False)  # DRAFT, COMPLETED
    reason = Column(String(100), nullable=False)  # DAMAGE, LOSS, FOUND, COUNT_CORRECTION, OTHER
    notes = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    warehouse = relationship("Warehouse")
    location = relationship("Location")
    bin = relationship("StorageBin")
    created_by = relationship("User")
    items = relationship("AdjustmentItem", back_populates="adjustment", cascade="all, delete-orphan")


class AdjustmentItem(Base, TimestampMixin):
    __tablename__ = "adjustment_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    adjustment_id = Column(String(36), ForeignKey("adjustments.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    recorded_quantity = Column(Integer, default=0, nullable=False)
    physical_quantity = Column(Integer, default=0, nullable=False)
    difference = Column(Integer, default=0, nullable=False)  # physical - recorded
    reason = Column(String(100), nullable=True)

    adjustment = relationship("Adjustment", back_populates="items")
    product = relationship("Product")


class Sale(Base, TimestampMixin):
    """Historical sales record for sales analytics."""
    __tablename__ = "sales"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    sale_number = Column(String(100), unique=True, nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    delivery_id = Column(String(36), ForeignKey("deliveries.id", ondelete="SET NULL"), nullable=True)
    total_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    sold_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    customer = relationship("Customer")
    warehouse = relationship("Warehouse")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")


class SaleItem(Base, TimestampMixin):
    __tablename__ = "sale_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    sale_id = Column(String(36), ForeignKey("sales.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    unit_price = Column(Numeric(12, 2), default=0.00, nullable=False)
    subtotal = Column(Numeric(12, 2), default=0.00, nullable=False)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")
