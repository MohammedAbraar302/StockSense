from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, TimestampMixin


class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    contact_person = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    organization = relationship("Organization", back_populates="warehouses")
    locations = relationship("Location", back_populates="warehouse", cascade="all, delete-orphan")


class Location(Base, TimestampMixin):
    __tablename__ = "locations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    location_type = Column(String(50), default="STORAGE", nullable=False)  # STORAGE, PRODUCTION, SCRAP, TRANSIT
    is_active = Column(Boolean, default=True, nullable=False)

    warehouse = relationship("Warehouse", back_populates="locations")
    bins = relationship("StorageBin", back_populates="location", cascade="all, delete-orphan")


class StorageBin(Base, TimestampMixin):
    __tablename__ = "storage_bins"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    location_id = Column(String(36), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    rack = Column(String(50), nullable=False)      # e.g., "Rack A", "Rack B", "Rack P01"
    bin_code = Column(String(50), nullable=False)  # e.g., "A01", "B01", "FG01"
    name = Column(String(255), nullable=False)      # e.g., "Rack A - Bin A01"
    max_capacity = Column(Integer, default=1000, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    location = relationship("Location", back_populates="bins")
