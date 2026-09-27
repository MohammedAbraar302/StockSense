import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_product_and_sku_uniqueness(client: AsyncClient, admin_auth_token: str):
    headers = {"Authorization": f"Bearer {admin_auth_token}"}

    prod_payload = {
        "name": "Industrial Ball Valve 3in",
        "sku": "VALVE-TEST-001",
        "unit_of_measure": "Pieces",
        "cost_price": "1200.00",
        "selling_price": "1750.00",
        "reorder_level": 10,
        "reorder_quantity": 25
    }

    # Create product
    res = await client.post("/api/v1/products", json=prod_payload, headers=headers)
    assert res.status_code == 200
    prod = res.json()
    assert prod["sku"] == "VALVE-TEST-001"

    # Duplicate SKU must fail with 400
    res_dup = await client.post("/api/v1/products", json=prod_payload, headers=headers)
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json()["error"]["message"]


@pytest.mark.asyncio
async def test_full_operational_scenario(client: AsyncClient, admin_auth_token: str):
    """
    Execute complete end-to-end scenario from Section 41:
    1. Create Product "Steel Rods Special" (SKU: STEEL-DEMO-01)
    2. Create Receipt 50 units
    3. Validate Receipt -> Inventory = +50, Ledger = +50
    4. Move 20 units Main Warehouse -> Production
    5. Warehouse Stock -20, Production Stock +20, 2 ledger entries
    6. Create Delivery 10 units -> Pick -> Pack -> Validate -> Inventory -10, Ledger -10
    7. Create Adjustment 3 units damaged -> Inventory -3, Ledger -3
    8. Check EOD reconciliation preview
    """
    headers = {"Authorization": f"Bearer {admin_auth_token}"}

    # Fetch Warehouses & Locations
    tree_res = await client.get("/api/v1/locations/tree", headers=headers)
    assert tree_res.status_code == 200
    whs = tree_res.json()["warehouses"]
    assert len(whs) >= 2
    wh1 = whs[0]
    wh2 = whs[1]
    wh1_loc = wh1["locations"][0]
    wh2_loc = wh2["locations"][0]

    # 1. Create Product
    prod_res = await client.post("/api/v1/products", json={
        "name": "Steel Rods Special",
        "sku": "STEEL-DEMO-01",
        "unit_of_measure": "Units",
        "cost_price": "500.00",
        "selling_price": "750.00",
        "reorder_level": 15,
        "reorder_quantity": 40
    }, headers=headers)
    assert prod_res.status_code == 200
    product_id = prod_res.json()["id"]

    # 2. Create Receipt 50 Units
    rec_res = await client.post("/api/v1/operations/receipts", json={
        "warehouse_id": wh1["id"],
        "notes": "Incoming 50 special steel rods",
        "items": [{
            "product_id": product_id,
            "location_id": wh1_loc["id"],
            "quantity_expected": 50,
            "quantity_received": 50,
            "unit_cost": "500.00"
        }]
    }, headers=headers)
    assert rec_res.status_code == 200
    receipt_id = rec_res.json()["id"]

    # 3. Validate Receipt
    val_rec = await client.post(f"/api/v1/operations/receipts/{receipt_id}/validate", headers=headers)
    assert val_rec.status_code == 200

    # Verify inventory increased to 50
    stock_res = await client.get(f"/api/v1/inventory/stock?warehouse_id={wh1['id']}&search=STEEL-DEMO-01", headers=headers)
    assert stock_res.status_code == 200
    items = stock_res.json()
    assert len(items) == 1
    assert items[0]["quantity_on_hand"] == 50

    # 4. Move 20 units Main Warehouse -> Production
    trf_res = await client.post("/api/v1/operations/transfers", json={
        "source_warehouse_id": wh1["id"],
        "source_location_id": wh1_loc["id"],
        "dest_warehouse_id": wh2["id"],
        "dest_location_id": wh2_loc["id"],
        "notes": "Transfer 20 units to production",
        "items": [{"product_id": product_id, "quantity": 20}]
    }, headers=headers)
    assert trf_res.status_code == 200
    transfer_id = trf_res.json()["id"]

    comp_trf = await client.post(f"/api/v1/operations/transfers/{transfer_id}/complete", headers=headers)
    assert comp_trf.status_code == 200

    # Check WH1 stock is 30, WH2 stock is 20 (Total still 50)
    stock_wh1 = await client.get(f"/api/v1/inventory/stock?warehouse_id={wh1['id']}&search=STEEL-DEMO-01", headers=headers)
    stock_wh2 = await client.get(f"/api/v1/inventory/stock?warehouse_id={wh2['id']}&search=STEEL-DEMO-01", headers=headers)
    assert stock_wh1.json()[0]["quantity_on_hand"] == 30
    assert stock_wh2.json()[0]["quantity_on_hand"] == 20

    # 5. Create Delivery 10 Units from WH1
    del_res = await client.post("/api/v1/operations/deliveries", json={
        "warehouse_id": wh1["id"],
        "notes": "Deliver 10 rods to customer",
        "items": [{
            "product_id": product_id,
            "location_id": wh1_loc["id"],
            "quantity_requested": 10,
            "unit_price": "750.00"
        }]
    }, headers=headers)
    assert del_res.status_code == 200
    delivery_id = del_res.json()["id"]

    await client.post(f"/api/v1/operations/deliveries/{delivery_id}/pick", headers=headers)
    await client.post(f"/api/v1/operations/deliveries/{delivery_id}/pack", headers=headers)
    val_del = await client.post(f"/api/v1/operations/deliveries/{delivery_id}/validate", headers=headers)
    assert val_del.status_code == 200

    # WH1 stock should now be 30 - 10 = 20
    stock_wh1_after = await client.get(f"/api/v1/inventory/stock?warehouse_id={wh1['id']}&search=STEEL-DEMO-01", headers=headers)
    assert stock_wh1_after.json()[0]["quantity_on_hand"] == 20

    # 6. Create Adjustment 3 Units Damaged in WH1
    # Current = 20, Physical = 17 (-3)
    adj_res = await client.post("/api/v1/operations/adjustments", json={
        "warehouse_id": wh1["id"],
        "location_id": wh1_loc["id"],
        "reason": "DAMAGE",
        "notes": "3 rods bent during handling",
        "items": [{
            "product_id": product_id,
            "physical_quantity": 17
        }]
    }, headers=headers)
    assert adj_res.status_code == 200

    stock_wh1_final = await client.get(f"/api/v1/inventory/stock?warehouse_id={wh1['id']}&search=STEEL-DEMO-01", headers=headers)
    assert stock_wh1_final.json()[0]["quantity_on_hand"] == 17

    # 7. Check EOD Reconciliation Preview
    eod_res = await client.get(f"/api/v1/reconciliation/preview?warehouse_id={wh1['id']}&location_id={wh1_loc['id']}", headers=headers)
    assert eod_res.status_code == 200
    preview = eod_res.json()
    rod_item = next((it for it in preview["items"] if it["product_id"] == product_id), None)
    assert rod_item is not None
    assert rod_item["current_system_stock"] == 17
