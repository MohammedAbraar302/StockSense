from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductDetailResponse,
    CategoryCreate,
    CategoryResponse,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=List[ProductResponse])
async def list_products(
    category_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    low_stock_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List catalog products with dynamic search, category filtering, and real-time stock balances.
    """
    products = await ProductService.get_products(
        db=db,
        org_id=current_user.organization_id,
        category_id=category_id,
        search=search,
        status=status,
        low_stock_only=low_stock_only
    )
    return products


@router.post("", response_model=ProductResponse)
async def create_product(
    req: ProductCreate,
    current_user: User = Depends(require_roles(["ADMIN", "INVENTORY_MANAGER"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new product with unique SKU and optional initial stock ledger transaction.
    """
    try:
        product = await ProductService.create_product(
            db=db,
            org_id=current_user.organization_id,
            name=req.name,
            sku=req.sku,
            category_id=req.category_id,
            unit_of_measure=req.unit_of_measure,
            description=req.description,
            cost_price=req.cost_price,
            selling_price=req.selling_price,
            reorder_level=req.reorder_level,
            reorder_quantity=req.reorder_quantity,
            initial_stock=req.initial_stock,
            initial_warehouse_id=req.initial_warehouse_id,
            initial_location_id=req.initial_location_id,
            initial_bin_id=req.initial_bin_id,
            user_id=current_user.id
        )

        detail = await ProductService.get_product_detail(db, product.id)
        return detail["product"]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List product categories."""
    cats = await ProductService.get_categories(db, current_user.organization_id)
    return cats


@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    req: CategoryCreate,
    current_user: User = Depends(require_roles(["ADMIN", "INVENTORY_MANAGER"])),
    db: AsyncSession = Depends(get_db)
):
    """Create product category."""
    cat = await ProductService.create_category(
        db=db,
        org_id=current_user.organization_id,
        name=req.name,
        code=req.code,
        description=req.description
    )
    return cat


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get full product details including multi-location stock positions and recent movements."""
    detail = await ProductService.get_product_detail(db, product_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return detail
