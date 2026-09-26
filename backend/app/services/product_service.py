from typing import List, Optional, Tuple, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from app.models.product import Product, Category, ReorderRule
from app.models.inventory import Inventory, InventoryMovement
from app.models.location import Warehouse, Location, StorageBin
from app.services.inventory_service import InventoryService
from app.services.audit_service import AuditService


class ProductService:
    @staticmethod
    async def create_category(
        db: AsyncSession,
        org_id: str,
        name: str,
        code: Optional[str] = None,
        description: Optional[str] = None
    ) -> Category:
        cat = Category(
            organization_id=org_id,
            name=name.strip(),
            code=code.strip().upper() if code else None,
            description=description
        )
        db.add(cat)
        await db.commit()
        await db.refresh(cat)
        return cat

    @staticmethod
    async def get_categories(db: AsyncSession, org_id: str) -> List[Category]:
        stmt = select(Category).where(Category.organization_id == org_id).order_by(Category.name.asc())
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def create_product(
        db: AsyncSession,
        org_id: str,
        name: str,
        sku: str,
        category_id: Optional[str],
        unit_of_measure: str,
        description: Optional[str],
        cost_price: Decimal,
        selling_price: Decimal,
        reorder_level: int,
        reorder_quantity: int,
        initial_stock: Optional[int] = None,
        initial_warehouse_id: Optional[str] = None,
        initial_location_id: Optional[str] = None,
        initial_bin_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Product:
        clean_sku = sku.strip().upper()

        # Check unique SKU in organization
        stmt = select(Product).where(and_(Product.organization_id == org_id, Product.sku == clean_sku))
        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            raise ValueError(f"A product with SKU '{clean_sku}' already exists.")

        product = Product(
            organization_id=org_id,
            sku=clean_sku,
            name=name.strip(),
            category_id=category_id,
            unit_of_measure=unit_of_measure.strip(),
            description=description,
            cost_price=cost_price,
            selling_price=selling_price,
            reorder_level=reorder_level,
            reorder_quantity=reorder_quantity,
            status="ACTIVE"
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)

        # If initial stock provided, execute initial ledger transaction
        if initial_stock and initial_stock > 0 and initial_warehouse_id and initial_location_id:
            await InventoryService.record_movement(
                db=db,
                product_id=product.id,
                warehouse_id=initial_warehouse_id,
                location_id=initial_location_id,
                bin_id=initial_bin_id,
                operation_type="INITIAL_STOCK",
                reference_type="INITIAL_STOCK",
                reference_id=product.id,
                quantity_change=initial_stock,
                user_id=user_id,
                notes=f"Initial stock upon product creation: {initial_stock} units"
            )
            await db.commit()

        await AuditService.log_action(
            db=db,
            action="PRODUCT_CREATED",
            entity="PRODUCT",
            entity_id=product.id,
            user_id=user_id,
            after_state={"sku": product.sku, "name": product.name, "initial_stock": initial_stock}
        )

        return product

    @staticmethod
    async def get_products(
        db: AsyncSession,
        org_id: str,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        low_stock_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Fetch products with aggregated stock counts and calculated stock statuses."""
        query = (
            select(Product, Category.name.label("category_name"))
            .outerjoin(Category, Product.category_id == Category.id)
            .where(Product.organization_id == org_id)
        )

        if category_id:
            query = query.where(Product.category_id == category_id)
        if status:
            query = query.where(Product.status == status)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(or_(Product.name.ilike(s), Product.sku.ilike(s)))

        query = query.order_by(Product.name.asc())
        result = await db.execute(query)
        rows = result.all()

        products_list = []
        for prod, cat_name in rows:
            # Query stock aggregates
            agg_stmt = (
                select(
                    func.coalesce(func.sum(Inventory.quantity_on_hand), 0).label("on_hand"),
                    func.coalesce(func.sum(Inventory.quantity_reserved), 0).label("reserved")
                )
                .where(Inventory.product_id == prod.id)
            )
            agg = (await db.execute(agg_stmt)).first()
            total_on_hand = agg.on_hand if agg else 0
            total_reserved = agg.reserved if agg else 0
            total_available = max(0, total_on_hand - total_reserved)

            if total_available == 0:
                stock_status = "OUT_OF_STOCK"
            elif total_available <= prod.reorder_level:
                stock_status = "LOW_STOCK"
            else:
                stock_status = "IN_STOCK"

            if low_stock_only and stock_status not in ["LOW_STOCK", "OUT_OF_STOCK"]:
                continue

            products_list.append({
                "id": prod.id,
                "organization_id": prod.organization_id,
                "sku": prod.sku,
                "name": prod.name,
                "category_id": prod.category_id,
                "category_name": cat_name,
                "unit_of_measure": prod.unit_of_measure,
                "description": prod.description,
                "cost_price": prod.cost_price,
                "selling_price": prod.selling_price,
                "reorder_level": prod.reorder_level,
                "reorder_quantity": prod.reorder_quantity,
                "status": prod.status,
                "total_on_hand": total_on_hand,
                "total_available": total_available,
                "total_reserved": total_reserved,
                "stock_status": stock_status,
                "created_at": prod.created_at
            })

        return products_list

    @staticmethod
    async def get_product_detail(db: AsyncSession, product_id: str) -> Optional[Dict[str, Any]]:
        """Fetch product with location-wise breakdown and recent ledger moves."""
        stmt = (
            select(Product, Category.name.label("category_name"))
            .outerjoin(Category, Product.category_id == Category.id)
            .where(Product.id == product_id)
        )
        row = (await db.execute(stmt)).first()
        if not row:
            return None

        prod, cat_name = row

        # Location-wise stock
        pos_stmt = (
            select(Inventory, Warehouse, Location, StorageBin)
            .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
            .join(Location, Inventory.location_id == Location.id)
            .outerjoin(StorageBin, Inventory.bin_id == StorageBin.id)
            .where(Inventory.product_id == prod.id)
        )
        positions = (await db.execute(pos_stmt)).all()

        location_breakdown = []
        total_on_hand = 0
        total_reserved = 0

        for inv, wh, loc, bin_obj in positions:
            on_hand = inv.quantity_on_hand or 0
            reserved = inv.quantity_reserved or 0
            total_on_hand += on_hand
            total_reserved += reserved

            location_breakdown.append({
                "warehouse_id": wh.id,
                "warehouse_name": wh.name,
                "location_id": loc.id,
                "location_name": loc.name,
                "bin_id": bin_obj.id if bin_obj else None,
                "bin_name": bin_obj.name if bin_obj else "General Area",
                "quantity_on_hand": on_hand,
                "quantity_reserved": reserved,
                "quantity_available": max(0, on_hand - reserved)
            })

        total_available = max(0, total_on_hand - total_reserved)
        if total_available == 0:
            stock_status = "OUT_OF_STOCK"
        elif total_available <= prod.reorder_level:
            stock_status = "LOW_STOCK"
        else:
            stock_status = "IN_STOCK"

        # Recent moves
        mv_stmt = (
            select(InventoryMovement, Warehouse.name.label("wh_name"), Location.name.label("loc_name"))
            .join(Warehouse, InventoryMovement.warehouse_id == Warehouse.id)
            .join(Location, InventoryMovement.location_id == Location.id)
            .where(InventoryMovement.product_id == prod.id)
            .order_by(InventoryMovement.created_at.desc())
            .limit(10)
        )
        recent_moves = [
            {
                "id": m.id,
                "operation_type": m.operation_type,
                "warehouse_name": wh_name,
                "location_name": loc_name,
                "quantity_change": m.quantity_change,
                "quantity_after": m.quantity_after,
                "created_at": m.created_at.isoformat()
            }
            for m, wh_name, loc_name in (await db.execute(mv_stmt)).all()
        ]

        return {
            "product": {
                "id": prod.id,
                "organization_id": prod.organization_id,
                "sku": prod.sku,
                "name": prod.name,
                "category_id": prod.category_id,
                "category_name": cat_name,
                "unit_of_measure": prod.unit_of_measure,
                "description": prod.description,
                "cost_price": prod.cost_price,
                "selling_price": prod.selling_price,
                "reorder_level": prod.reorder_level,
                "reorder_quantity": prod.reorder_quantity,
                "status": prod.status,
                "total_on_hand": total_on_hand,
                "total_available": total_available,
                "total_reserved": total_reserved,
                "stock_status": stock_status,
                "created_at": prod.created_at
            },
            "stock_locations": location_breakdown,
            "recent_movements": recent_moves
        }
