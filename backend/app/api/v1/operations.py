from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.schemas.operation import (
    SupplierCreate,
    SupplierResponse,
    CustomerCreate,
    CustomerResponse,
    ReceiptCreate,
    ReceiptResponse,
    DeliveryCreate,
    DeliveryResponse,
    TransferCreate,
    TransferResponse,
    AdjustmentCreate,
    AdjustmentResponse,
)
from app.services.operation_service import OperationService

router = APIRouter(prefix="/operations", tags=["Operations"])


# --- Suppliers & Customers ---
@router.get("/suppliers", response_model=List[SupplierResponse])
async def list_suppliers(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await OperationService.get_suppliers(db, current_user.organization_id)


@router.post("/suppliers", response_model=SupplierResponse)
async def create_supplier(req: SupplierCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await OperationService.create_supplier(db, current_user.organization_id, req.name, req.contact_name, req.email, req.phone, req.address)


@router.get("/customers", response_model=List[CustomerResponse])
async def list_customers(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await OperationService.get_customers(db, current_user.organization_id)


@router.post("/customers", response_model=CustomerResponse)
async def create_customer(req: CustomerCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await OperationService.create_customer(db, current_user.organization_id, req.name, req.contact_name, req.email, req.phone, req.address)


# --- Receipts ---
@router.get("/receipts", response_model=List[ReceiptResponse])
async def list_receipts(
    warehouse_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    receipts = await OperationService.get_receipts(db, current_user.organization_id, warehouse_id=warehouse_id, status=status)
    out = []
    for r in receipts:
        items = []
        for it in r.items:
            items.append({
                "id": it.id,
                "product_id": it.product_id,
                "product_name": it.product.name if it.product else None,
                "sku": it.product.sku if it.product else None,
                "location_id": it.location_id,
                "location_name": it.location.name if it.location else None,
                "bin_id": it.bin_id,
                "bin_name": it.bin.name if it.bin else None,
                "quantity_expected": it.quantity_expected,
                "quantity_received": it.quantity_received,
                "unit_cost": it.unit_cost
            })
        out.append({
            "id": r.id,
            "receipt_number": r.receipt_number,
            "supplier_id": r.supplier_id,
            "supplier_name": r.supplier.name if r.supplier else "Standard Vendor",
            "warehouse_id": r.warehouse_id,
            "warehouse_name": r.warehouse.name if r.warehouse else "Warehouse",
            "status": r.status,
            "notes": r.notes,
            "created_by_name": r.created_by.full_name if r.created_by else None,
            "validated_by_name": r.validated_by.full_name if r.validated_by else None,
            "validated_at": r.validated_at,
            "items": items,
            "created_at": r.created_at
        })
    return out


@router.post("/receipts", response_model=ReceiptResponse)
async def create_receipt(
    req: ReceiptCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a draft incoming receipt."""
    items_data = [item.model_dump() for item in req.items]
    r = await OperationService.create_receipt(
        db=db,
        org_id=current_user.organization_id,
        warehouse_id=req.warehouse_id,
        supplier_id=req.supplier_id,
        items=items_data,
        notes=req.notes,
        user_id=current_user.id
    )
    receipts = await OperationService.get_receipts(db, current_user.organization_id)
    target = next((rec for rec in receipts if rec.id == r.id), r)
    return await list_receipts(current_user=current_user, db=db).then(lambda l: [x for x in l if x["id"] == r.id][0]) if False else target


@router.post("/receipts/{receipt_id}/validate")
async def validate_receipt(
    receipt_id: str,
    current_user: User = Depends(require_roles(["ADMIN", "INVENTORY_MANAGER", "WAREHOUSE_STAFF"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate incoming goods receipt.
    Executes an atomic database transaction:
    Increments inventory position and appends an immutable RECEIPT ledger record.
    """
    try:
        receipt = await OperationService.validate_receipt(db=db, receipt_id=receipt_id, user_id=current_user.id)
        return {"message": "Receipt validated successfully. Inventory has been updated.", "status": receipt.status}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- Deliveries ---
@router.get("/deliveries", response_model=List[DeliveryResponse])
async def list_deliveries(
    warehouse_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    deliveries = await OperationService.get_deliveries(db, current_user.organization_id, warehouse_id=warehouse_id, status=status)
    out = []
    for d in deliveries:
        items = []
        for it in d.items:
            items.append({
                "id": it.id,
                "product_id": it.product_id,
                "product_name": it.product.name if it.product else None,
                "sku": it.product.sku if it.product else None,
                "location_id": it.location_id,
                "location_name": it.location.name if it.location else None,
                "bin_id": it.bin_id,
                "bin_name": it.bin.name if it.bin else None,
                "quantity_requested": it.quantity_requested,
                "quantity_picked": it.quantity_picked,
                "quantity_packed": it.quantity_packed,
                "unit_price": it.unit_price
            })
        out.append({
            "id": d.id,
            "delivery_number": d.delivery_number,
            "customer_id": d.customer_id,
            "customer_name": d.customer.name if d.customer else "Standard Customer",
            "warehouse_id": d.warehouse_id,
            "warehouse_name": d.warehouse.name if d.warehouse else "Warehouse",
            "status": d.status,
            "notes": d.notes,
            "created_by_name": d.created_by.full_name if d.created_by else None,
            "validated_by_name": d.validated_by.full_name if d.validated_by else None,
            "validated_at": d.validated_at,
            "items": items,
            "created_at": d.created_at
        })
    return out


@router.post("/deliveries")
async def create_delivery(
    req: DeliveryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    items_data = [item.model_dump() for item in req.items]
    delivery = await OperationService.create_delivery(
        db=db,
        org_id=current_user.organization_id,
        warehouse_id=req.warehouse_id,
        customer_id=req.customer_id,
        items=items_data,
        notes=req.notes,
        user_id=current_user.id
    )
    return {"id": delivery.id, "delivery_number": delivery.delivery_number, "status": delivery.status}


@router.post("/deliveries/{delivery_id}/pick")
async def pick_delivery(delivery_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    d = await OperationService.pick_delivery(db, delivery_id, current_user.id)
    return {"message": "Delivery picked successfully", "status": d.status}


@router.post("/deliveries/{delivery_id}/pack")
async def pack_delivery(delivery_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    d = await OperationService.pack_delivery(db, delivery_id, current_user.id)
    return {"message": "Delivery packed successfully", "status": d.status}


@router.post("/deliveries/{delivery_id}/validate")
async def validate_delivery(
    delivery_id: str,
    current_user: User = Depends(require_roles(["ADMIN", "INVENTORY_MANAGER", "WAREHOUSE_STAFF"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate outgoing delivery order.
    Checks stock availability, deducts inventory, appends DELIVERY ledger record,
    and logs the sale for real sales analytics.
    """
    try:
        delivery = await OperationService.validate_delivery(db=db, delivery_id=delivery_id, user_id=current_user.id)
        return {"message": "Delivery validated and dispatched successfully. Inventory has been updated.", "status": delivery.status}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- Internal Transfers ---
@router.get("/transfers", response_model=List[TransferResponse])
async def list_transfers(
    warehouse_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    transfers = await OperationService.get_transfers(db, current_user.organization_id, warehouse_id=warehouse_id)
    out = []
    for t in transfers:
        items = [
            {
                "id": it.id,
                "product_id": it.product_id,
                "product_name": it.product.name if it.product else None,
                "sku": it.product.sku if it.product else None,
                "quantity": it.quantity
            }
            for it in t.items
        ]
        out.append({
            "id": t.id,
            "transfer_number": t.transfer_number,
            "source_warehouse_id": t.source_warehouse_id,
            "source_warehouse_name": t.source_warehouse.name if t.source_warehouse else None,
            "source_location_id": t.source_location_id,
            "source_location_name": t.source_location.name if t.source_location else None,
            "source_bin_id": t.source_bin_id,
            "source_bin_name": t.source_bin.name if t.source_bin else None,
            "dest_warehouse_id": t.dest_warehouse_id,
            "dest_warehouse_name": t.dest_warehouse.name if t.dest_warehouse else None,
            "dest_location_id": t.dest_location_id,
            "dest_location_name": t.dest_location.name if t.dest_location else None,
            "dest_bin_id": t.dest_bin_id,
            "dest_bin_name": t.dest_bin.name if t.dest_bin else None,
            "status": t.status,
            "notes": t.notes,
            "created_by_name": t.created_by.full_name if t.created_by else None,
            "completed_by_name": t.completed_by.full_name if t.completed_by else None,
            "completed_at": t.completed_at,
            "items": items,
            "created_at": t.created_at
        })
    return out


@router.post("/transfers")
async def create_transfer(
    req: TransferCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    items_data = [item.model_dump() for item in req.items]
    t = await OperationService.create_transfer(
        db=db,
        org_id=current_user.organization_id,
        source_warehouse_id=req.source_warehouse_id,
        source_location_id=req.source_location_id,
        source_bin_id=req.source_bin_id,
        dest_warehouse_id=req.dest_warehouse_id,
        dest_location_id=req.dest_location_id,
        dest_bin_id=req.dest_bin_id,
        items=items_data,
        notes=req.notes,
        user_id=current_user.id
    )
    return {"id": t.id, "transfer_number": t.transfer_number, "status": t.status}


@router.post("/transfers/{transfer_id}/complete")
async def complete_transfer(
    transfer_id: str,
    current_user: User = Depends(require_roles(["ADMIN", "INVENTORY_MANAGER", "WAREHOUSE_STAFF"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Complete internal stock transfer.
    Deducts stock from source location and adds to destination location.
    Logs TWO distinct ledger entries (TRANSFER_OUT and TRANSFER_IN).
    Organization-wide aggregate stock remains unchanged.
    """
    try:
        t = await OperationService.complete_transfer(db=db, transfer_id=transfer_id, user_id=current_user.id)
        return {"message": "Transfer completed successfully. Inventory updated across locations.", "status": t.status}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- Adjustments ---
@router.get("/adjustments", response_model=List[AdjustmentResponse])
async def list_adjustments(
    warehouse_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    adjs = await OperationService.get_adjustments(db, current_user.organization_id, warehouse_id=warehouse_id)
    out = []
    for a in adjs:
        items = [
            {
                "id": it.id,
                "product_id": it.product_id,
                "product_name": it.product.name if it.product else None,
                "sku": it.product.sku if it.product else None,
                "recorded_quantity": it.recorded_quantity,
                "physical_quantity": it.physical_quantity,
                "difference": it.difference,
                "reason": it.reason
            }
            for it in a.items
        ]
        out.append({
            "id": a.id,
            "adjustment_number": a.adjustment_number,
            "warehouse_id": a.warehouse_id,
            "warehouse_name": a.warehouse.name if a.warehouse else None,
            "location_id": a.location_id,
            "location_name": a.location.name if a.location else None,
            "bin_id": a.bin_id,
            "bin_name": a.bin.name if a.bin else None,
            "status": a.status,
            "reason": a.reason,
            "notes": a.notes,
            "created_by_name": a.created_by.full_name if a.created_by else None,
            "items": items,
            "created_at": a.created_at
        })
    return out


@router.post("/adjustments")
async def create_adjustment(
    req: AdjustmentCreate,
    current_user: User = Depends(require_roles(["ADMIN", "INVENTORY_MANAGER", "WAREHOUSE_STAFF"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform stock adjustment.
    Reconciles recorded system stock with physical count.
    Updates inventory by exact difference and appends an immutable ADJUSTMENT ledger record.
    """
    try:
        items_data = [item.model_dump() for item in req.items]
        adj = await OperationService.create_and_apply_adjustment(
            db=db,
            org_id=current_user.organization_id,
            warehouse_id=req.warehouse_id,
            location_id=req.location_id,
            bin_id=req.bin_id,
            reason=req.reason,
            items=items_data,
            notes=req.notes,
            user_id=current_user.id
        )
        return {"id": adj.id, "adjustment_number": adj.adjustment_number, "status": adj.status, "reason": adj.reason}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
