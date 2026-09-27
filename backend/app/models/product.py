from sqlalchemy import Column, String, Boolean, ForeignKey, Numeric, Integer, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, TimestampMixin


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)

    products = relationship("Product", back_populates="category")


class UnitOfMeasure(Base, TimestampMixin):
    __tablename__ = "units_of_measure"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(50), nullable=False)  # Kilogram, Unit, Piece, Meter, Box
    abbreviation = Column(String(20), nullable=False, unique=True)  # kg, pcs, m, box


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    sku = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    unit_of_measure = Column(String(50), default="Units", nullable=False)
    description = Column(Text, nullable=True)
    cost_price = Column(Numeric(12, 2), default=0.00, nullable=False)
    selling_price = Column(Numeric(12, 2), default=0.00, nullable=False)
    reorder_level = Column(Integer, default=10, nullable=False)
    reorder_quantity = Column(Integer, default=50, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, INACTIVE, DISCONTINUED

    organization = relationship("Organization", back_populates="products")
    category = relationship("Category", back_populates="products")
    inventory_positions = relationship("Inventory", back_populates="product", cascade="all, delete-orphan")
    reorder_rules = relationship("ReorderRule", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("organization_id", "sku", name="uq_org_sku"),
    )


class ReorderRule(Base, TimestampMixin):
    __tablename__ = "reorder_rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    min_quantity = Column(Integer, default=10, nullable=False)
    max_quantity = Column(Integer, default=100, nullable=False)

    product = relationship("Product", back_populates="reorder_rules")
