from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.schemas.location import (
    WarehouseCreate,
    WarehouseResponse,
    LocationCreate,
    LocationResponse,
    StorageBinCreate,
    StorageBinResponse,
    GlobalLocationTreeResponse,
)
from app.services.location_service import LocationService

router = APIRouter(prefix="/locations", tags=["Warehouses & Locations"])


@router.get("/warehouses", response_model=List[WarehouseResponse])
async def list_warehouses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all warehouses with child locations and storage bins."""
    warehouses = await LocationService.get_warehouses(db, current_user.organization_id)
    return warehouses


@router.post("/warehouses", response_model=WarehouseResponse)
async def create_warehouse(
    req: WarehouseCreate,
    current_user: User = Depends(require_roles(["ADMIN", "INVENTORY_MANAGER"])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new physical warehouse facility."""
    try:
        warehouse = await LocationService.create_warehouse(
            db=db,
            org_id=current_user.organization_id,
            code=req.code,
            name=req.name,
            address=req.address,
            contact_person=req.contact_person,
            user_id=current_user.id
        )
        return warehouse
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/tree", response_model=GlobalLocationTreeResponse)
async def get_global_location_tree(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Return hierarchical location tree for the Global Top Navigation Selector:
    ALL LOCATIONS -> WAREHOUSE -> LOCATION -> RACK / BIN
    """
    tree = await LocationService.get_location_tree(db, current_user.organization_id)
    return tree


@router.post("/locations", response_model=LocationResponse)
async def create_sub_location(
    req: LocationCreate,
    current_user: User = Depends(require_roles(["ADMIN", "INVENTORY_MANAGER"])),
    db: AsyncSession = Depends(get_db)
):
    """Create a sub-location (e.g. Storage Zone, Production Floor, Finished Goods)."""
    try:
        location = await LocationService.create_location(
            db=db,
            warehouse_id=req.warehouse_id,
            code=req.code,
            name=req.name,
            location_type=req.location_type,
            user_id=current_user.id
        )
        return location
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/bins", response_model=StorageBinResponse)
async def create_bin(
    req: StorageBinCreate,
    current_user: User = Depends(require_roles(["ADMIN", "INVENTORY_MANAGER"])),
    db: AsyncSession = Depends(get_db)
):
    """Create a specific rack / storage bin."""
    try:
        b = await LocationService.create_storage_bin(
            db=db,
            location_id=req.location_id,
            rack=req.rack,
            bin_code=req.bin_code,
            name=req.name,
            max_capacity=req.max_capacity,
            user_id=current_user.id
        )
        return b
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
