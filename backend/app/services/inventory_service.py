from typing import List, Optional, Tuple, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from app.models.inventory import Inventory, InventoryMovement
from app.models.product import Product, Category
from app.models.location import Warehouse, Location, StorageBin
from app.models.user import User
from app.services.audit_service import AuditService


class InventoryService:
    @staticmethod
    async def get_or_create_position(
        db: AsyncSession,
        product_id: str,
        warehouse_id: str,
        location_id: str,
        bin_id: Optional[str] = None
    ) -> Inventory:
        """Fetch inventory position with lock (or create if not existing)."""
        stmt = (
            select(Inventory)
            .where(
                and_(
                    Inventory.product_id == product_id,
                    Inventory.warehouse_id == warehouse_id,
                    Inventory.location_id == location_id,
                    Inventory.bin_id == bin_id
                )
            )
            .with_for_update()
        )
        position = (await db.execute(stmt)).scalars().first()

        if not position:
            position = Inventory(
                product_id=product_id,
                warehouse_id=warehouse_id,
                location_id=location_id,
                bin_id=bin_id,
                quantity_on_hand=0,
                quantity_reserved=0,
                quantity_damaged=0
            )
            db.add(position)
            await db.flush()

        return position

    @staticmethod
    async def record_movement(
        db: AsyncSession,
        product_id: str,
        warehouse_id: str,
        location_id: str,
        operation_type: str,
        reference_type: str,
        reference_id: Optional[str],
        quantity_change: int,
        user_id: Optional[str] = None,
        bin_id: Optional[str] = None,
        notes: Optional[str] = None,
        is_damaged: bool = False
    ) -> InventoryMovement:
        """
        ATOMIC INVENTORY TRANSACTION & IMMUTABLE LEDGER RECORD:
        1. Acquire row lock on inventory position.
        2. Verify stock non-negative invariant.
        3. Compute before & after quantities.
        4. Mutate inventory position.
        5. Insert append-only ledger entry.
        6. Trigger low-stock alerts if needed.
        """
        position = await InventoryService.get_or_create_position(
            db=db,
            product_id=product_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            bin_id=bin_id
        )

        qty_before = position.quantity_on_hand
        qty_after = qty_before + quantity_change

        if qty_after < 0:
            product = (await db.execute(select(Product).where(Product.id == product_id))).scalars().first()
            p_name = product.name if product else product_id
            raise ValueError(
                f"Insufficient inventory for {p_name}. Available: {qty_before}, requested reduction: {abs(quantity_change)}"
            )

        position.quantity_on_hand = qty_after

        if is_damaged:
            position.quantity_damaged += abs(quantity_change)

        # Create immutable ledger entry
        ledger_entry = InventoryMovement(
            product_id=product_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            bin_id=bin_id,
            operation_type=operation_type,
            reference_type=reference_type,
            reference_id=reference_id,
            quantity_before=qty_before,
            quantity_change=quantity_change,
            quantity_after=qty_after,
            user_id=user_id,
            notes=notes
        )
        db.add(ledger_entry)
        await db.flush()

        # Check for low-stock condition
        await InventoryService.check_low_stock_and_notify(db, product_id, user_id)

        return ledger_entry

    @staticmethod
    async def check_low_stock_and_notify(
        db: AsyncSession,
        product_id: str,
        user_id: Optional[str] = None
    ) -> None:
        """Evaluate aggregate product stock against reorder_level."""
        product = (await db.execute(select(Product).where(Product.id == product_id))).scalars().first()
        if not product:
            return

        total_stmt = select(func.sum(Inventory.quantity_on_hand)).where(Inventory.product_id == product_id)
        total_on_hand = (await db.execute(total_stmt)).scalar() or 0

        reserved_stmt = select(func.sum(Inventory.quantity_reserved)).where(Inventory.product_id == product_id)
        total_reserved = (await db.execute(reserved_stmt)).scalar() or 0

        available = max(0, total_on_hand - total_reserved)

        if available == 0:
            await AuditService.notify(
                db=db,
                notification_type="OUT_OF_STOCK",
                title=f"Out of Stock: {product.name}",
                message=f"Product '{product.name}' (SKU: {product.sku}) is completely OUT OF STOCK.",
                link=f"/products/{product.id}"
            )
        elif available <= product.reorder_level:
            await AuditService.notify(
                db=db,
                notification_type="LOW_STOCK",
                title=f"Low Stock Alert: {product.name}",
                message=f"Product '{product.name}' has {available} units available (Reorder level: {product.reorder_level}).",
                link=f"/products/{product.id}"
            )

    @staticmethod
    async def get_stock_positions(
        db: AsyncSession,
        org_id: str,
        warehouse_id: Optional[str] = None,
        location_id: Optional[str] = None,
        bin_id: Optional[str] = None,
        category_id: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch stock positions across the organization with hierarchical filtering."""
        query = (
            select(
                Inventory,
                Product,
                Category,
                Warehouse,
                Location,
                StorageBin
            )
            .join(Product, Inventory.product_id == Product.id)
            .outerjoin(Category, Product.category_id == Category.id)
            .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
            .join(Location, Inventory.location_id == Location.id)
            .outerjoin(StorageBin, Inventory.bin_id == StorageBin.id)
            .where(Warehouse.organization_id == org_id)
        )

        if warehouse_id:
            query = query.where(Inventory.warehouse_id == warehouse_id)
        if location_id:
            query = query.where(Inventory.location_id == location_id)
        if bin_id:
            query = query.where(Inventory.bin_id == bin_id)
        if category_id:
            query = query.where(Product.category_id == category_id)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(or_(Product.name.ilike(s), Product.sku.ilike(s)))

        result = await db.execute(query)
        rows = result.all()

        stock_list = []
        for inv, prod, cat, wh, loc, bin_obj in rows:
            on_hand = inv.quantity_on_hand or 0
            reserved = inv.quantity_reserved or 0
            avail = max(0, on_hand - reserved)
            cost = prod.cost_price or Decimal("0.00")
            valuation = cost * on_hand

            stock_list.append({
                "id": inv.id,
                "product_id": prod.id,
                "product_name": prod.name,
                "sku": prod.sku,
                "category_name": cat.name if cat else "Uncategorized",
                "warehouse_id": wh.id,
                "warehouse_name": wh.name,
                "location_id": loc.id,
                "location_name": loc.name,
                "bin_id": bin_obj.id if bin_obj else None,
                "bin_name": bin_obj.name if bin_obj else "General Area",
                "quantity_on_hand": on_hand,
                "quantity_reserved": reserved,
                "quantity_available": avail,
                "quantity_damaged": inv.quantity_damaged or 0,
                "unit_of_measure": prod.unit_of_measure,
                "cost_price": cost,
                "total_valuation": valuation
            })
        return stock_list

    @staticmethod
    async def get_ledger(
        db: AsyncSession,
        org_id: str,
        warehouse_id: Optional[str] = None,
        location_id: Optional[str] = None,
        bin_id: Optional[str] = None,
        product_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Fetch historical movement ledger with filters and pagination."""
        query = (
            select(
                InventoryMovement,
                Product,
                Warehouse,
                Location,
                StorageBin,
                User
            )
            .join(Product, InventoryMovement.product_id == Product.id)
            .join(Warehouse, InventoryMovement.warehouse_id == Warehouse.id)
            .join(Location, InventoryMovement.location_id == Location.id)
            .outerjoin(StorageBin, InventoryMovement.bin_id == StorageBin.id)
            .outerjoin(User, InventoryMovement.user_id == User.id)
            .where(Warehouse.organization_id == org_id)
        )

        if warehouse_id:
            query = query.where(InventoryMovement.warehouse_id == warehouse_id)
        if location_id:
            query = query.where(InventoryMovement.location_id == location_id)
        if bin_id:
            query = query.where(InventoryMovement.bin_id == bin_id)
        if product_id:
            query = query.where(InventoryMovement.product_id == product_id)
        if operation_type:
            query = query.where(InventoryMovement.operation_type == operation_type)

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Order by newest
        query = query.order_by(InventoryMovement.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        rows = result.all()

        movements = []
        for mv, prod, wh, loc, bin_obj, user in rows:
            movements.append({
                "id": mv.id,
                "product_id": prod.id,
                "product_name": prod.name,
                "sku": prod.sku,
                "warehouse_id": wh.id,
                "warehouse_name": wh.name,
                "location_id": loc.id,
                "location_name": loc.name,
                "bin_id": bin_obj.id if bin_obj else None,
                "bin_name": bin_obj.name if bin_obj else "General Area",
                "operation_type": mv.operation_type,
                "reference_type": mv.reference_type,
                "reference_id": mv.reference_id,
                "quantity_before": mv.quantity_before,
                "quantity_change": mv.quantity_change,
                "quantity_after": mv.quantity_after,
                "user_name": user.full_name if user else "System Automated",
                "notes": mv.notes,
                "created_at": mv.created_at
            })

        return movements, total
