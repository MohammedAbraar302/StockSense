import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from app.models.operation import (
    Supplier,
    Customer,
    Receipt,
    ReceiptItem,
    Delivery,
    DeliveryItem,
    Transfer,
    TransferItem,
    Adjustment,
    AdjustmentItem,
    Sale,
    SaleItem,
)
from app.models.product import Product
from app.models.location import Warehouse, Location, StorageBin
from app.models.user import User
from app.services.inventory_service import InventoryService
from app.services.audit_service import AuditService


class OperationService:
    # ----------------------------------------------------
    # SUPPLIERS & CUSTOMERS
    # ----------------------------------------------------
    @staticmethod
    async def create_supplier(db: AsyncSession, org_id: str, name: str, contact_name: Optional[str], email: Optional[str], phone: Optional[str], address: Optional[str]) -> Supplier:
        supplier = Supplier(organization_id=org_id, name=name.strip(), contact_name=contact_name, email=email, phone=phone, address=address)
        db.add(supplier)
        await db.commit()
        await db.refresh(supplier)
        return supplier

    @staticmethod
    async def get_suppliers(db: AsyncSession, org_id: str) -> List[Supplier]:
        stmt = select(Supplier).where(Supplier.organization_id == org_id).order_by(Supplier.name.asc())
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def create_customer(db: AsyncSession, org_id: str, name: str, contact_name: Optional[str], email: Optional[str], phone: Optional[str], address: Optional[str]) -> Customer:
        customer = Customer(organization_id=org_id, name=name.strip(), contact_name=contact_name, email=email, phone=phone, address=address)
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        return customer

    @staticmethod
    async def get_customers(db: AsyncSession, org_id: str) -> List[Customer]:
        stmt = select(Customer).where(Customer.organization_id == org_id).order_by(Customer.name.asc())
        return list((await db.execute(stmt)).scalars().all())

    # ----------------------------------------------------
    # RECEIPTS (Incoming Stock)
    # ----------------------------------------------------
    @staticmethod
    async def create_receipt(
        db: AsyncSession,
        org_id: str,
        warehouse_id: str,
        supplier_id: Optional[str],
        items: List[Dict[str, Any]],
        notes: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Receipt:
        receipt_num = f"REC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        receipt = Receipt(
            organization_id=org_id,
            receipt_number=receipt_num,
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            status="DRAFT",
            notes=notes,
            created_by_id=user_id
        )
        db.add(receipt)
        await db.flush()

        for item_data in items:
            item = ReceiptItem(
                receipt_id=receipt.id,
                product_id=item_data["product_id"],
                location_id=item_data["location_id"],
                bin_id=item_data.get("bin_id"),
                quantity_expected=item_data.get("quantity_expected", 1),
                quantity_received=item_data.get("quantity_received", item_data.get("quantity_expected", 1)),
                unit_cost=Decimal(str(item_data.get("unit_cost", "0.00")))
            )
            db.add(item)

        await db.commit()
        await db.refresh(receipt)
        return receipt

    @staticmethod
    async def validate_receipt(
        db: AsyncSession,
        receipt_id: str,
        user_id: Optional[str] = None
    ) -> Receipt:
        """
        ATOMIC RECEIPT VALIDATION:
        1. Lock receipt and verify status != DONE (Idempotency protection).
        2. Iterate over items: increment stock via InventoryService.record_movement.
        3. Create append-only ledger entries (RECEIPT).
        4. Mark status = DONE.
        5. Record audit log.
        """
        stmt = (
            select(Receipt)
            .options(selectinload(Receipt.items))
            .where(Receipt.id == receipt_id)
            .with_for_update()
        )
        receipt = (await db.execute(stmt)).scalars().first()
        if not receipt:
            raise ValueError("Receipt not found")

        if receipt.status == "DONE":
            raise ValueError("Receipt has already been validated and processed (Idempotent guard).")

        if receipt.status == "CANCELED":
            raise ValueError("Cannot validate a canceled receipt.")

        # Update stock for each item in this database transaction
        for item in receipt.items:
            await InventoryService.record_movement(
                db=db,
                product_id=item.product_id,
                warehouse_id=receipt.warehouse_id,
                location_id=item.location_id,
                bin_id=item.bin_id,
                operation_type="RECEIPT",
                reference_type="RECEIPT",
                reference_id=receipt.receipt_number,
                quantity_change=item.quantity_received,
                user_id=user_id,
                notes=f"Receipt {receipt.receipt_number} from supplier"
            )

        receipt.status = "DONE"
        receipt.validated_by_id = user_id
        receipt.validated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(receipt)

        await AuditService.log_action(
            db=db,
            action="RECEIPT_VALIDATED",
            entity="RECEIPT",
            entity_id=receipt.id,
            user_id=user_id,
            after_state={"receipt_number": receipt.receipt_number, "status": "DONE"}
        )

        return receipt

    @staticmethod
    async def get_receipts(
        db: AsyncSession,
        org_id: str,
        warehouse_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Receipt]:
        query = (
            select(Receipt)
            .options(
                selectinload(Receipt.supplier),
                selectinload(Receipt.warehouse),
                selectinload(Receipt.items).selectinload(ReceiptItem.product),
                selectinload(Receipt.items).selectinload(ReceiptItem.location),
                selectinload(Receipt.items).selectinload(ReceiptItem.bin),
                selectinload(Receipt.created_by),
                selectinload(Receipt.validated_by)
            )
            .where(Receipt.organization_id == org_id)
        )
        if warehouse_id:
            query = query.where(Receipt.warehouse_id == warehouse_id)
        if status:
            query = query.where(Receipt.status == status)

        query = query.order_by(Receipt.created_at.desc())
        return list((await db.execute(query)).scalars().all())

    # ----------------------------------------------------
    # DELIVERIES (Outgoing Stock)
    # ----------------------------------------------------
    @staticmethod
    async def create_delivery(
        db: AsyncSession,
        org_id: str,
        warehouse_id: str,
        customer_id: Optional[str],
        items: List[Dict[str, Any]],
        notes: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Delivery:
        delivery_num = f"DEL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        delivery = Delivery(
            organization_id=org_id,
            delivery_number=delivery_num,
            customer_id=customer_id,
            warehouse_id=warehouse_id,
            status="DRAFT",
            notes=notes,
            created_by_id=user_id
        )
        db.add(delivery)
        await db.flush()

        for item_data in items:
            item = DeliveryItem(
                delivery_id=delivery.id,
                product_id=item_data["product_id"],
                location_id=item_data["location_id"],
                bin_id=item_data.get("bin_id"),
                quantity_requested=item_data.get("quantity_requested", 1),
                quantity_picked=item_data.get("quantity_picked", 0),
                quantity_packed=item_data.get("quantity_packed", 0),
                unit_price=Decimal(str(item_data.get("unit_price", "0.00")))
            )
            db.add(item)

        await db.commit()
        await db.refresh(delivery)
        return delivery

    @staticmethod
    async def pick_delivery(db: AsyncSession, delivery_id: str, user_id: Optional[str] = None) -> Delivery:
        stmt = select(Delivery).options(selectinload(Delivery.items)).where(Delivery.id == delivery_id)
        delivery = (await db.execute(stmt)).scalars().first()
        if not delivery:
            raise ValueError("Delivery not found")
        for item in delivery.items:
            item.quantity_picked = item.quantity_requested
        delivery.status = "PICKED"
        await db.commit()
        await db.refresh(delivery)
        return delivery

    @staticmethod
    async def pack_delivery(db: AsyncSession, delivery_id: str, user_id: Optional[str] = None) -> Delivery:
        stmt = select(Delivery).options(selectinload(Delivery.items)).where(Delivery.id == delivery_id)
        delivery = (await db.execute(stmt)).scalars().first()
        if not delivery:
            raise ValueError("Delivery not found")
        for item in delivery.items:
            item.quantity_packed = item.quantity_picked or item.quantity_requested
        delivery.status = "PACKED"
        await db.commit()
        await db.refresh(delivery)
        return delivery

    @staticmethod
    async def validate_delivery(
        db: AsyncSession,
        delivery_id: str,
        user_id: Optional[str] = None
    ) -> Delivery:
        """
        ATOMIC DELIVERY VALIDATION:
        1. Lock delivery and verify status != DONE (Idempotency protection).
        2. Verify sufficient stock at each item position.
        3. Deduct stock via InventoryService.record_movement (negative change).
        4. Create append-only ledger entries (DELIVERY).
        5. Create Sale and SaleItem records for live analytics.
        6. Mark status = DONE.
        7. Record audit log.
        """
        stmt = (
            select(Delivery)
            .options(selectinload(Delivery.items))
            .where(Delivery.id == delivery_id)
            .with_for_update()
        )
        delivery = (await db.execute(stmt)).scalars().first()
        if not delivery:
            raise ValueError("Delivery not found")

        if delivery.status == "DONE":
            raise ValueError("Delivery has already been validated and dispatched (Idempotent guard).")

        if delivery.status == "CANCELED":
            raise ValueError("Cannot validate a canceled delivery.")

        total_sale_amount = Decimal("0.00")
        sale_items_data = []

        # Deduct stock for each item
        for item in delivery.items:
            qty_to_deliver = item.quantity_packed or item.quantity_picked or item.quantity_requested
            await InventoryService.record_movement(
                db=db,
                product_id=item.product_id,
                warehouse_id=delivery.warehouse_id,
                location_id=item.location_id,
                bin_id=item.bin_id,
                operation_type="DELIVERY",
                reference_type="DELIVERY",
                reference_id=delivery.delivery_number,
                quantity_change=-qty_to_deliver,
                user_id=user_id,
                notes=f"Delivery {delivery.delivery_number} to customer"
            )
            subtotal = Decimal(str(item.unit_price)) * Decimal(str(qty_to_deliver))
            total_sale_amount += subtotal
            sale_items_data.append({
                "product_id": item.product_id,
                "quantity": qty_to_deliver,
                "unit_price": item.unit_price,
                "subtotal": subtotal
            })

        # Record Sale for real analytics
        sale = Sale(
            organization_id=delivery.organization_id,
            sale_number=f"SO-{delivery.delivery_number}",
            customer_id=delivery.customer_id,
            warehouse_id=delivery.warehouse_id,
            delivery_id=delivery.id,
            total_amount=total_sale_amount,
            sold_at=datetime.now(timezone.utc)
        )
        db.add(sale)
        await db.flush()

        for s_item in sale_items_data:
            db.add(SaleItem(
                sale_id=sale.id,
                product_id=s_item["product_id"],
                quantity=s_item["quantity"],
                unit_price=s_item["unit_price"],
                subtotal=s_item["subtotal"]
            ))

        delivery.status = "DONE"
        delivery.validated_by_id = user_id
        delivery.validated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(delivery)

        await AuditService.log_action(
            db=db,
            action="DELIVERY_VALIDATED",
            entity="DELIVERY",
            entity_id=delivery.id,
            user_id=user_id,
            after_state={"delivery_number": delivery.delivery_number, "status": "DONE"}
        )

        return delivery

    @staticmethod
    async def get_deliveries(
        db: AsyncSession,
        org_id: str,
        warehouse_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Delivery]:
        query = (
            select(Delivery)
            .options(
                selectinload(Delivery.customer),
                selectinload(Delivery.warehouse),
                selectinload(Delivery.items).selectinload(DeliveryItem.product),
                selectinload(Delivery.items).selectinload(DeliveryItem.location),
                selectinload(Delivery.items).selectinload(DeliveryItem.bin),
                selectinload(Delivery.created_by),
                selectinload(Delivery.validated_by)
            )
            .where(Delivery.organization_id == org_id)
        )
        if warehouse_id:
            query = query.where(Delivery.warehouse_id == warehouse_id)
        if status:
            query = query.where(Delivery.status == status)

        query = query.order_by(Delivery.created_at.desc())
        return list((await db.execute(query)).scalars().all())

    # ----------------------------------------------------
    # INTERNAL TRANSFERS
    # ----------------------------------------------------
    @staticmethod
    async def create_transfer(
        db: AsyncSession,
        org_id: str,
        source_warehouse_id: str,
        source_location_id: str,
        dest_warehouse_id: str,
        dest_location_id: str,
        items: List[Dict[str, Any]],
        source_bin_id: Optional[str] = None,
        dest_bin_id: Optional[str] = None,
        notes: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Transfer:
        transfer_num = f"TRF-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        transfer = Transfer(
            organization_id=org_id,
            transfer_number=transfer_num,
            source_warehouse_id=source_warehouse_id,
            source_location_id=source_location_id,
            source_bin_id=source_bin_id,
            dest_warehouse_id=dest_warehouse_id,
            dest_location_id=dest_location_id,
            dest_bin_id=dest_bin_id,
            status="DRAFT",
            notes=notes,
            created_by_id=user_id
        )
        db.add(transfer)
        await db.flush()

        for item_data in items:
            item = TransferItem(
                transfer_id=transfer.id,
                product_id=item_data["product_id"],
                quantity=item_data["quantity"]
            )
            db.add(item)

        await db.commit()
        await db.refresh(transfer)
        return transfer

    @staticmethod
    async def complete_transfer(
        db: AsyncSession,
        transfer_id: str,
        user_id: Optional[str] = None
    ) -> Transfer:
        """
        ATOMIC TRANSFER EXECUTION:
        1. Lock transfer and verify status != DONE (Idempotency protection).
        2. Deduct from source position (-Qty, TRANSFER_OUT).
        3. Add to destination position (+Qty, TRANSFER_IN).
        4. Generate TWO distinct ledger records.
        5. Total company inventory remains mathematically unchanged.
        6. Mark status = DONE.
        7. Record audit log.
        """
        stmt = (
            select(Transfer)
            .options(selectinload(Transfer.items))
            .where(Transfer.id == transfer_id)
            .with_for_update()
        )
        transfer = (await db.execute(stmt)).scalars().first()
        if not transfer:
            raise ValueError("Transfer not found")

        if transfer.status == "DONE":
            raise ValueError("Transfer has already been completed (Idempotent guard).")

        for item in transfer.items:
            # 1. Source deduct
            await InventoryService.record_movement(
                db=db,
                product_id=item.product_id,
                warehouse_id=transfer.source_warehouse_id,
                location_id=transfer.source_location_id,
                bin_id=transfer.source_bin_id,
                operation_type="TRANSFER_OUT",
                reference_type="TRANSFER",
                reference_id=transfer.transfer_number,
                quantity_change=-item.quantity,
                user_id=user_id,
                notes=f"Internal transfer {transfer.transfer_number} OUT to dest location"
            )

            # 2. Destination add
            await InventoryService.record_movement(
                db=db,
                product_id=item.product_id,
                warehouse_id=transfer.dest_warehouse_id,
                location_id=transfer.dest_location_id,
                bin_id=transfer.dest_bin_id,
                operation_type="TRANSFER_IN",
                reference_type="TRANSFER",
                reference_id=transfer.transfer_number,
                quantity_change=item.quantity,
                user_id=user_id,
                notes=f"Internal transfer {transfer.transfer_number} IN from source location"
            )

        transfer.status = "DONE"
        transfer.completed_by_id = user_id
        transfer.completed_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(transfer)

        await AuditService.log_action(
            db=db,
            action="TRANSFER_COMPLETED",
            entity="TRANSFER",
            entity_id=transfer.id,
            user_id=user_id,
            after_state={"transfer_number": transfer.transfer_number, "status": "DONE"}
        )

        return transfer

    @staticmethod
    async def get_transfers(db: AsyncSession, org_id: str, warehouse_id: Optional[str] = None) -> List[Transfer]:
        query = (
            select(Transfer)
            .options(
                selectinload(Transfer.source_warehouse),
                selectinload(Transfer.source_location),
                selectinload(Transfer.source_bin),
                selectinload(Transfer.dest_warehouse),
                selectinload(Transfer.dest_location),
                selectinload(Transfer.dest_bin),
                selectinload(Transfer.items).selectinload(TransferItem.product),
                selectinload(Transfer.created_by),
                selectinload(Transfer.completed_by)
            )
            .where(Transfer.organization_id == org_id)
        )
        if warehouse_id:
            query = query.where(or_(Transfer.source_warehouse_id == warehouse_id, Transfer.dest_warehouse_id == warehouse_id))

        query = query.order_by(Transfer.created_at.desc())
        return list((await db.execute(query)).scalars().all())

    # ----------------------------------------------------
    # ADJUSTMENTS (Physical Count Reconciliation)
    # ----------------------------------------------------
    @staticmethod
    async def create_and_apply_adjustment(
        db: AsyncSession,
        org_id: str,
        warehouse_id: str,
        location_id: str,
        reason: str,
        items: List[Dict[str, Any]],
        bin_id: Optional[str] = None,
        notes: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Adjustment:
        """
        ATOMIC STOCK ADJUSTMENT:
        1. Query recorded system stock at location/bin.
        2. Compute difference = physical - recorded.
        3. Adjust stock by exact difference via InventoryService.record_movement.
        4. Log immutable ADJUSTMENT ledger entry with mandatory reason.
        5. Record audit log.
        """
        adj_num = f"ADJ-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        adjustment = Adjustment(
            organization_id=org_id,
            adjustment_number=adj_num,
            warehouse_id=warehouse_id,
            location_id=location_id,
            bin_id=bin_id,
            status="COMPLETED",
            reason=reason,
            notes=notes,
            created_by_id=user_id
        )
        db.add(adjustment)
        await db.flush()

        for item_data in items:
            p_id = item_data["product_id"]
            phys_qty = item_data["physical_quantity"]

            # Current system stock
            pos = await InventoryService.get_or_create_position(
                db=db,
                product_id=p_id,
                warehouse_id=warehouse_id,
                location_id=location_id,
                bin_id=bin_id
            )
            rec_qty = pos.quantity_on_hand
            diff = phys_qty - rec_qty

            adj_item = AdjustmentItem(
                adjustment_id=adjustment.id,
                product_id=p_id,
                recorded_quantity=rec_qty,
                physical_quantity=phys_qty,
                difference=diff,
                reason=item_data.get("reason", reason)
            )
            db.add(adj_item)

            if diff != 0:
                is_damaged = (reason == "DAMAGE")
                await InventoryService.record_movement(
                    db=db,
                    product_id=p_id,
                    warehouse_id=warehouse_id,
                    location_id=location_id,
                    bin_id=bin_id,
                    operation_type="ADJUSTMENT",
                    reference_type="ADJUSTMENT",
                    reference_id=adjustment.adjustment_number,
                    quantity_change=diff,
                    user_id=user_id,
                    notes=f"Adjustment {adj_num} ({reason}): {diff} diff",
                    is_damaged=is_damaged
                )

        await db.commit()
        await db.refresh(adjustment)

        await AuditService.log_action(
            db=db,
            action="ADJUSTMENT_PERFORMED",
            entity="ADJUSTMENT",
            entity_id=adjustment.id,
            user_id=user_id,
            after_state={"adjustment_number": adjustment.adjustment_number, "reason": reason}
        )

        return adjustment

    @staticmethod
    async def get_adjustments(db: AsyncSession, org_id: str, warehouse_id: Optional[str] = None) -> List[Adjustment]:
        query = (
            select(Adjustment)
            .options(
                selectinload(Adjustment.warehouse),
                selectinload(Adjustment.location),
                selectinload(Adjustment.bin),
                selectinload(Adjustment.items).selectinload(AdjustmentItem.product),
                selectinload(Adjustment.created_by)
            )
            .where(Adjustment.organization_id == org_id)
        )
        if warehouse_id:
            query = query.where(Adjustment.warehouse_id == warehouse_id)

        query = query.order_by(Adjustment.created_at.desc())
        return list((await db.execute(query)).scalars().all())
