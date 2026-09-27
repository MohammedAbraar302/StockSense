from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.models.location import Warehouse, Location, StorageBin
from app.models.user import Organization
from app.services.audit_service import AuditService


class LocationService:
    @staticmethod
    async def get_warehouses(db: AsyncSession, org_id: str) -> List[Warehouse]:
        """Fetch all warehouses with locations and bins."""
        stmt = (
            select(Warehouse)
            .where(Warehouse.organization_id == org_id)
            .options(
                selectinload(Warehouse.locations).selectinload(Location.bins)
            )
            .order_by(Warehouse.name.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_warehouse(
        db: AsyncSession,
        org_id: str,
        code: str,
        name: str,
        address: Optional[str] = None,
        contact_person: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Warehouse:
        warehouse = Warehouse(
            organization_id=org_id,
            code=code.strip().upper(),
            name=name.strip(),
            address=address,
            contact_person=contact_person,
            is_active=True
        )
        db.add(warehouse)
        await db.commit()
        await db.refresh(warehouse)

        # Create default Location and Storage Bin for easy initial receipting
        default_loc = Location(
            warehouse_id=warehouse.id,
            code=f"{warehouse.code}-LOC-01",
            name=f"{warehouse.name} General Storage",
            location_type="STORAGE",
            is_active=True
        )
        db.add(default_loc)
        await db.commit()
        await db.refresh(default_loc)

        default_bin = StorageBin(
            location_id=default_loc.id,
            rack="Rack A",
            bin_code="A01",
            name="Rack A - Bin A01",
            max_capacity=2000,
            is_active=True
        )
        db.add(default_bin)
        await db.commit()

        await AuditService.log_action(
            db=db,
            action="WAREHOUSE_CREATED",
            entity="WAREHOUSE",
            entity_id=warehouse.id,
            user_id=user_id,
            after_state={"code": warehouse.code, "name": warehouse.name}
        )

        return warehouse

    @staticmethod
    async def create_location(
        db: AsyncSession,
        warehouse_id: str,
        code: str,
        name: str,
        location_type: str = "STORAGE",
        user_id: Optional[str] = None
    ) -> Location:
        location = Location(
            warehouse_id=warehouse_id,
            code=code.strip().upper(),
            name=name.strip(),
            location_type=location_type.upper(),
            is_active=True
        )
        db.add(location)
        await db.commit()
        await db.refresh(location)

        await AuditService.log_action(
            db=db,
            action="LOCATION_CREATED",
            entity="LOCATION",
            entity_id=location.id,
            user_id=user_id,
            after_state={"code": location.code, "name": location.name}
        )
        return location

    @staticmethod
    async def create_storage_bin(
        db: AsyncSession,
        location_id: str,
        rack: str,
        bin_code: str,
        name: str,
        max_capacity: int = 1000,
        user_id: Optional[str] = None
    ) -> StorageBin:
        storage_bin = StorageBin(
            location_id=location_id,
            rack=rack.strip(),
            bin_code=bin_code.strip().upper(),
            name=name.strip(),
            max_capacity=max_capacity,
            is_active=True
        )
        db.add(storage_bin)
        await db.commit()
        await db.refresh(storage_bin)

        await AuditService.log_action(
            db=db,
            action="STORAGE_BIN_CREATED",
            entity="STORAGE_BIN",
            entity_id=storage_bin.id,
            user_id=user_id,
            after_state={"rack": storage_bin.rack, "bin_code": storage_bin.bin_code}
        )
        return storage_bin

    @staticmethod
    async def get_location_tree(db: AsyncSession, org_id: str) -> dict:
        """
        Build nested tree:
        Warehouse -> Locations -> Storage Bins
        Used by the Global Location Selector in the Top Navigation bar.
        """
        warehouses = await LocationService.get_warehouses(db, org_id)
        tree = []
        for wh in warehouses:
            wh_item = {
                "id": wh.id,
                "code": wh.code,
                "name": wh.name,
                "locations": []
            }
            for loc in wh.locations:
                loc_item = {
                    "id": loc.id,
                    "code": loc.code,
                    "name": loc.name,
                    "location_type": loc.location_type,
                    "bins": [
                        {
                            "id": b.id,
                            "rack": b.rack,
                            "bin_code": b.bin_code,
                            "name": b.name
                        }
                        for b in loc.bins
                    ]
                }
                wh_item["locations"].append(loc_item)
            tree.append(wh_item)
        return {"warehouses": tree}
