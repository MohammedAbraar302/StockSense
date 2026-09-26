from datetime import datetime, date, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from app.models.reconciliation import DailyClosing, DailyClosingItem
from app.models.inventory import Inventory, InventoryMovement
from app.models.product import Product
from app.models.location import Warehouse, Location
from app.services.audit_service import AuditService


class ReconciliationService:
    @staticmethod
    async def get_eod_preview(
        db: AsyncSession,
        warehouse_id: str,
        location_id: str,
        target_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Compute mathematical expected closing stock for all products at a location:
        Expected = Opening + Receipts - Deliveries + Transfers In - Transfers Out ± Adjustments
        """
        if not target_date:
            target_date = date.today()

        # Check if already closed today
        exist_stmt = select(DailyClosing).where(
            and_(
                DailyClosing.location_id == location_id,
                DailyClosing.closing_date == target_date
            )
        )
        existing_closing = (await db.execute(exist_stmt)).scalars().first()

        wh = (await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))).scalars().first()
        loc = (await db.execute(select(Location).where(Location.id == location_id))).scalars().first()

        # Fetch all active products
        prod_stmt = select(Product).where(Product.organization_id == wh.organization_id).order_by(Product.name.asc())
        products = (await db.execute(prod_stmt)).scalars().all()

        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())

        rows = []
        for prod in products:
            # Current inventory position
            pos_stmt = select(Inventory.quantity_on_hand).where(
                and_(
                    Inventory.product_id == prod.id,
                    Inventory.location_id == location_id
                )
            )
            current_stock = (await db.execute(pos_stmt)).scalar() or 0

            # Today's movements by operation type
            moves_stmt = select(
                InventoryMovement.operation_type,
                func.coalesce(func.sum(InventoryMovement.quantity_change), 0).label("qty_sum")
            ).where(
                and_(
                    InventoryMovement.product_id == prod.id,
                    InventoryMovement.location_id == location_id,
                    InventoryMovement.created_at >= start_of_day,
                    InventoryMovement.created_at <= end_of_day
                )
            ).group_by(InventoryMovement.operation_type)

            moves_by_type = {row[0]: row[1] for row in (await db.execute(moves_stmt)).all()}

            receipts = abs(moves_by_type.get("RECEIPT", 0))
            deliveries = abs(moves_by_type.get("DELIVERY", 0))
            transfers_in = abs(moves_by_type.get("TRANSFER_IN", 0))
            transfers_out = abs(moves_by_type.get("TRANSFER_OUT", 0))
            adjustments = moves_by_type.get("ADJUSTMENT", 0)

            # Net today movement = receipts - deliveries + transfers_in - transfers_out + adjustments
            net_movement_today = receipts - deliveries + transfers_in - transfers_out + adjustments

            # Opening stock = current_stock - net_movement_today
            opening_stock = max(0, current_stock - net_movement_today)

            expected_closing = opening_stock + receipts - deliveries + transfers_in - transfers_out + adjustments

            rows.append({
                "product_id": prod.id,
                "product_name": prod.name,
                "sku": prod.sku,
                "unit_of_measure": prod.unit_of_measure,
                "opening_stock": opening_stock,
                "receipts": receipts,
                "deliveries": deliveries,
                "transfers_in": transfers_in,
                "transfers_out": transfers_out,
                "adjustments": adjustments,
                "expected_stock": expected_closing,
                "current_system_stock": current_stock
            })

        return {
            "warehouse_id": warehouse_id,
            "warehouse_name": wh.name if wh else "Warehouse",
            "location_id": location_id,
            "location_name": loc.name if loc else "Location",
            "target_date": target_date,
            "is_already_closed": bool(existing_closing),
            "existing_closing_id": existing_closing.id if existing_closing else None,
            "items": rows
        }

    @staticmethod
    async def close_eod(
        db: AsyncSession,
        org_id: str,
        warehouse_id: str,
        location_id: str,
        items_input: List[Dict[str, Any]],
        closing_date: Optional[date] = None,
        notes: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> DailyClosing:
        """
        Record verified physical closing count, compute variance, and enforce mandatory explanation.
        """
        if not closing_date:
            closing_date = date.today()

        # Check duplicate closing
        exist_stmt = select(DailyClosing).where(
            and_(
                DailyClosing.location_id == location_id,
                DailyClosing.closing_date == closing_date
            )
        )
        if (await db.execute(exist_stmt)).scalars().first():
            raise ValueError(f"Daily closing for this location on {closing_date} has already been submitted.")

        # Compute preview to obtain authoritative expected stock
        preview = await ReconciliationService.get_eod_preview(db, warehouse_id, location_id, closing_date)
        preview_map = {item["product_id"]: item for item in preview["items"]}

        daily_closing = DailyClosing(
            organization_id=org_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            closing_date=closing_date,
            status="CLOSED",
            notes=notes,
            closed_by_id=user_id,
            closed_at=datetime.now(timezone.utc)
        )
        db.add(daily_closing)
        await db.flush()

        has_variance = False
        for item_in in items_input:
            p_id = item_in["product_id"]
            phys_qty = item_in["physical_quantity"]
            explanation = item_in.get("explanation")

            calc = preview_map.get(p_id, {})
            expected_qty = calc.get("expected_stock", 0)
            variance = phys_qty - expected_qty

            if variance != 0:
                has_variance = True
                if not explanation or not explanation.strip():
                    raise ValueError(
                        f"Explanation is strictly required for stock variance on {calc.get('product_name', p_id)} (Variance: {variance})."
                    )

            closing_item = DailyClosingItem(
                daily_closing_id=daily_closing.id,
                product_id=p_id,
                opening_quantity=calc.get("opening_stock", 0),
                receipts_quantity=calc.get("receipts", 0),
                deliveries_quantity=calc.get("deliveries", 0),
                transfers_in_quantity=calc.get("transfers_in", 0),
                transfers_out_quantity=calc.get("transfers_out", 0),
                adjustments_quantity=calc.get("adjustments", 0),
                expected_quantity=expected_qty,
                physical_quantity=phys_qty,
                variance=variance,
                explanation=explanation
            )
            db.add(closing_item)

        await db.commit()
        await db.refresh(daily_closing)

        if has_variance:
            await AuditService.notify(
                db=db,
                notification_type="STOCK_VARIANCE",
                title=f"EOD Stock Variance Logged: {preview['location_name']}",
                message=f"End-of-day reconciliation for {closing_date} recorded inventory variances.",
                link="/reports"
            )

        await AuditService.log_action(
            db=db,
            action="EOD_CLOSED",
            entity="DAILY_CLOSING",
            entity_id=daily_closing.id,
            user_id=user_id,
            after_state={"location_id": location_id, "closing_date": str(closing_date), "has_variance": has_variance}
        )

        return daily_closing

    @staticmethod
    async def get_closing_history(
        db: AsyncSession,
        org_id: str,
        warehouse_id: Optional[str] = None
    ) -> List[DailyClosing]:
        query = (
            select(DailyClosing)
            .options(
                selectinload(DailyClosing.warehouse),
                selectinload(DailyClosing.location),
                selectinload(DailyClosing.closed_by),
                selectinload(DailyClosing.items).selectinload(DailyClosingItem.product)
            )
            .where(DailyClosing.organization_id == org_id)
        )
        if warehouse_id:
            query = query.where(DailyClosing.warehouse_id == warehouse_id)

        query = query.order_by(DailyClosing.closing_date.desc(), DailyClosing.created_at.desc())
        return list((await db.execute(query)).scalars().all())
