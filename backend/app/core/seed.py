import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import Organization, Role, Permission, User, UserRole
from app.models.location import Warehouse, Location, StorageBin
from app.models.product import Category, UnitOfMeasure, Product
from app.models.operation import Supplier, Customer, Sale, SaleItem
from app.models.audit import Notification
from app.services.inventory_service import InventoryService
from app.services.operation_service import OperationService

logger = logging.getLogger("stocksense.seed")


async def seed_demo_data() -> None:
    """Idempotently seed comprehensive realistic enterprise data."""
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        existing_org = (await db.execute(select(Organization).where(Organization.slug == "default"))).scalars().first()
        if existing_org:
            user_count = len((await db.execute(select(User).where(User.organization_id == existing_org.id))).scalars().all())
            if user_count >= 3:
                logger.info("Demo data already populated. Skipping seed.")
                return

        logger.info("Starting fresh database seeding...")

        # 1. Organization
        org = Organization(
            name="StockSense Enterprises Ltd.",
            slug="default",
            is_active=True
        )
        db.add(org)
        await db.commit()
        await db.refresh(org)

        # 2. Roles & Permissions
        roles = {}
        for r_name, r_desc in [
            ("ADMIN", "System Administrator with full organizational oversight"),
            ("INVENTORY_MANAGER", "Inventory & Operations Manager with approval authority"),
            ("WAREHOUSE_STAFF", "Warehouse floor associate for picking, packing & stock counts"),
        ]:
            r_obj = Role(name=r_name, description=r_desc)
            db.add(r_obj)
            roles[r_name] = r_obj

        await db.commit()
        for k in roles:
            await db.refresh(roles[k])

        # 3. Demo Users
        admin_user = User(
            organization_id=org.id,
            email="admin@stocksense.local",
            mobile="9876543210",
            hashed_password=get_password_hash("AdminPass@123"),
            full_name="Rajesh Sharma (Admin)",
            is_active=True,
            is_verified=True
        )
        db.add(admin_user)

        manager_user = User(
            organization_id=org.id,
            email="manager@stocksense.local",
            mobile="9876543211",
            hashed_password=get_password_hash("ManagerPass@123"),
            full_name="Priya Patel (Inventory Mgr)",
            is_active=True,
            is_verified=True
        )
        db.add(manager_user)

        staff_user = User(
            organization_id=org.id,
            email="staff@stocksense.local",
            mobile="9876543212",
            hashed_password=get_password_hash("StaffPass@123"),
            full_name="Amit Kumar (Warehouse Staff)",
            is_active=True,
            is_verified=True
        )
        db.add(staff_user)
        await db.commit()

        await db.refresh(admin_user)
        await db.refresh(manager_user)
        await db.refresh(staff_user)

        db.add(UserRole(user_id=admin_user.id, role_id=roles["ADMIN"].id))
        db.add(UserRole(user_id=manager_user.id, role_id=roles["INVENTORY_MANAGER"].id))
        db.add(UserRole(user_id=staff_user.id, role_id=roles["WAREHOUSE_STAFF"].id))
        await db.commit()

        # 4. Warehouses & Hierarchical Locations
        wh1 = Warehouse(
            organization_id=org.id,
            code="WH-MAIN",
            name="Main Central Warehouse",
            address="Plot 42, Industrial Area Phase 1, Gurgaon, HR",
            contact_person="Ramesh Gupta",
            is_active=True
        )
        wh2 = Warehouse(
            organization_id=org.id,
            code="WH-PROD",
            name="Industrial Production Hub",
            address="Sector 18, Electronic City, Bengaluru, KA",
            contact_person="Kavita Reddy",
            is_active=True
        )
        wh3 = Warehouse(
            organization_id=org.id,
            code="WH-DIST",
            name="Finished Goods Distribution Center",
            address="Bhiwandi Logistics Park, Mumbai, MH",
            contact_person="Suresh Verma",
            is_active=True
        )
        db.add_all([wh1, wh2, wh3])
        await db.commit()
        for wh in [wh1, wh2, wh3]:
            await db.refresh(wh)

        # Locations
        loc1_1 = Location(warehouse_id=wh1.id, code="WH1-STORE", name="Primary Storage Zone", location_type="STORAGE", is_active=True)
        loc1_2 = Location(warehouse_id=wh1.id, code="WH1-RECV", name="Receiving Bay 01", location_type="STORAGE", is_active=True)
        loc2_1 = Location(warehouse_id=wh2.id, code="WH2-FLOOR", name="Production Floor P01", location_type="PRODUCTION", is_active=True)
        loc2_2 = Location(warehouse_id=wh2.id, code="WH2-ASSEMBLY", name="Assembly Line Section B", location_type="PRODUCTION", is_active=True)
        loc3_1 = Location(warehouse_id=wh3.id, code="WH3-DISP", name="Finished Goods Staging", location_type="STORAGE", is_active=True)
        db.add_all([loc1_1, loc1_2, loc2_1, loc2_2, loc3_1])
        await db.commit()
        for loc in [loc1_1, loc1_2, loc2_1, loc2_2, loc3_1]:
            await db.refresh(loc)

        # Storage Bins
        bin1 = StorageBin(location_id=loc1_1.id, rack="Rack A", bin_code="A01", name="Rack A - Bin A01", max_capacity=2000, is_active=True)
        bin2 = StorageBin(location_id=loc1_1.id, rack="Rack A", bin_code="A02", name="Rack A - Bin A02", max_capacity=2000, is_active=True)
        bin3 = StorageBin(location_id=loc1_1.id, rack="Rack B", bin_code="B01", name="Rack B - Bin B01", max_capacity=1500, is_active=True)
        bin4 = StorageBin(location_id=loc2_1.id, rack="Rack P01", bin_code="P01", name="Production Rack P01", max_capacity=1000, is_active=True)
        bin5 = StorageBin(location_id=loc3_1.id, rack="Rack FG", bin_code="FG01", name="Finished Goods Rack FG01", max_capacity=3000, is_active=True)
        db.add_all([bin1, bin2, bin3, bin4, bin5])
        await db.commit()
        for b in [bin1, bin2, bin3, bin4, bin5]:
            await db.refresh(b)

        # 5. Categories
        cat_map = {}
        for c_name, c_code in [
            ("Raw Materials & Metals", "METALS"),
            ("Building & Construction", "CONSTR"),
            ("Electrical & Wiring", "ELEC"),
            ("Industrial Hardware", "HARDW"),
            ("Safety & PPE", "SAFETY"),
            ("Office & Infrastructure", "OFFICE"),
        ]:
            cat = Category(organization_id=org.id, name=c_name, code=c_code)
            db.add(cat)
            cat_map[c_name] = cat
        await db.commit()
        for k in cat_map:
            await db.refresh(cat_map[k])

        # 6. Suppliers & Customers
        suppliers = []
        for s_name, s_email, s_phone in [
            ("Tata Steel Direct", "sales@tatasteel.com", "+91 22 6665 8282"),
            ("UltraTech Cement Logistics", "orders@ultratech.com", "+91 22 6691 7800"),
            ("Havells Industrial Supply", "b2b@havells.com", "+91 120 4771000"),
            ("Schneider Electrical Ltd", "distributors@se.com", "+91 11 4159 0000"),
            ("3M Safety Solutions India", "safety.in@mmm.com", "+91 80 2223 1414"),
        ]:
            s = Supplier(organization_id=org.id, name=s_name, email=s_email, phone=s_phone, contact_name="Commercial Dept")
            db.add(s)
            suppliers.append(s)

        customers = []
        for c_name, c_email, c_phone in [
            ("Larsen & Toubro Heavy Civil", "procurement@larsentoubro.com", "+91 22 6752 5656"),
            ("Godrej Properties Infra", "orders@godrejproperties.com", "+91 22 6166 9600"),
            ("Reliance Infrastructure Ltd", "projects@relianceinfra.com", "+91 22 3038 6000"),
            ("Apex Engineering Works", "contact@apexeng.in", "+91 11 2345 6789"),
            ("Metro Rail Contractors JV", "tenders@metrorailjv.in", "+91 44 2827 1234"),
        ]:
            c = Customer(organization_id=org.id, name=c_name, email=c_email, phone=c_phone, contact_name="Site Manager")
            db.add(c)
            customers.append(c)

        await db.commit()
        for s in suppliers:
            await db.refresh(s)
        for c in customers:
            await db.refresh(c)

        # 7. 20+ Realistic Products with Initial Stock Positions & Ledger Entries
        product_specs = [
            ("Steel Rods 12mm TMT", "STEEL-001", "Raw Materials & Metals", "Bags/Tons", Decimal("4500.00"), Decimal("5200.00"), 20, 50, 150),
            ("UltraTech Cement Bags 50kg", "CEMENT-001", "Building & Construction", "Bags", Decimal("380.00"), Decimal("440.00"), 50, 100, 300),
            ("Ergonomic Office Chairs", "CHAIR-001", "Office & Infrastructure", "Units", Decimal("4200.00"), Decimal("6500.00"), 10, 25, 45),
            ("Industrial Hex Bolts M10", "BOLT-001", "Industrial Hardware", "Boxes", Decimal("250.00"), Decimal("380.00"), 30, 80, 200),
            ("PVC Heavy Pipes 4in x 6m", "PVC-001", "Building & Construction", "Pieces", Decimal("650.00"), Decimal("850.00"), 15, 40, 90),
            ("Copper Electrical Wire 2.5mm", "WIRE-001", "Electrical & Wiring", "Rolls", Decimal("1800.00"), Decimal("2300.00"), 25, 60, 120),
            ("Hard Hat Safety Helmets", "HELM-001", "Safety & PPE", "Pieces", Decimal("320.00"), Decimal("490.00"), 20, 50, 80),
            ("LED Industrial Floodlight 100W", "LED-001", "Electrical & Wiring", "Units", Decimal("1250.00"), Decimal("1850.00"), 10, 30, 40),
            ("Stainless Steel Ball Valves 2in", "VALVE-001", "Industrial Hardware", "Pieces", Decimal("890.00"), Decimal("1350.00"), 15, 35, 60),
            ("Hydraulic High-Pressure Hose", "HOSE-001", "Industrial Hardware", "Meters", Decimal("420.00"), Decimal("620.00"), 20, 50, 75),
            ("Angle Iron 50x50x5mm", "IRON-001", "Raw Materials & Metals", "Lengths", Decimal("1100.00"), Decimal("1450.00"), 15, 40, 110),
            ("Welding Electrodes E6013 3.15mm", "WELD-001", "Industrial Hardware", "Packets", Decimal("450.00"), Decimal("650.00"), 25, 70, 140),
            ("Precision Ball Bearings 6204-2RS", "BEAR-001", "Industrial Hardware", "Pieces", Decimal("180.00"), Decimal("290.00"), 40, 100, 220),
            ("Polycarbonate Roofing Sheet 10ft", "ROOF-001", "Building & Construction", "Sheets", Decimal("1400.00"), Decimal("1950.00"), 10, 30, 35),
            ("Aluminum Composite Panel 4x8ft", "ACP-001", "Building & Construction", "Panels", Decimal("2200.00"), Decimal("2900.00"), 10, 25, 50),
            ("Heavy Duty Leather Work Gloves", "GLOVE-001", "Safety & PPE", "Pairs", Decimal("120.00"), Decimal("220.00"), 50, 150, 5),  # Intentionally low stock for alert!
            ("Hydraulic Pallet Jack 2.5 Ton", "JACK-001", "Office & Infrastructure", "Units", Decimal("14500.00"), Decimal("19500.00"), 2, 5, 8),
            ("Industrial Measuring Tape 50m", "TAPE-001", "Industrial Hardware", "Units", Decimal("350.00"), Decimal("550.00"), 15, 30, 0),  # Out of stock for alert!
            ("Epoxy Floor Paint Grey 20L", "PAINT-001", "Building & Construction", "Buckets", Decimal("3800.00"), Decimal("5100.00"), 8, 20, 22),
            ("Galvanized Binding Wire 18 Gauge", "GWIRE-001", "Raw Materials & Metals", "Bundles", Decimal("850.00"), Decimal("1150.00"), 20, 50, 65),
            ("High-Visibility Safety Vests", "VEST-001", "Safety & PPE", "Pieces", Decimal("150.00"), Decimal("280.00"), 30, 80, 180),
        ]

        products = []
        for name, sku, cat_name, uom, cost, sell, reorder_lvl, reorder_qty, initial_qty in product_specs:
            cat = cat_map[cat_name]
            p = Product(
                organization_id=org.id,
                sku=sku,
                name=name,
                category_id=cat.id,
                unit_of_measure=uom,
                description=f"Standard enterprise grade {name} conforming to IS/ISO specifications.",
                cost_price=cost,
                selling_price=sell,
                reorder_level=reorder_lvl,
                reorder_quantity=reorder_qty,
                status="ACTIVE"
            )
            db.add(p)
            await db.flush()
            products.append((p, initial_qty))

        await db.commit()

        # 8. Record Initial Stock Movement in Ledger
        for p, init_qty in products:
            if init_qty > 0:
                await InventoryService.record_movement(
                    db=db,
                    product_id=p.id,
                    warehouse_id=wh1.id,
                    location_id=loc1_1.id,
                    bin_id=bin1.id,
                    operation_type="INITIAL_STOCK",
                    reference_type="INITIAL_STOCK",
                    reference_id="SEED-INIT",
                    quantity_change=init_qty,
                    user_id=admin_user.id,
                    notes="Baseline stock on system initialization"
                )

        await db.commit()

        # 9. Create a Sample Validated Receipt (Incoming +50 Steel Rods)
        steel_prod = next(p for p, _ in products if p.sku == "STEEL-001")
        rec = await OperationService.create_receipt(
            db=db,
            org_id=org.id,
            warehouse_id=wh1.id,
            supplier_id=suppliers[0].id,
            items=[{
                "product_id": steel_prod.id,
                "location_id": loc1_1.id,
                "bin_id": bin1.id,
                "quantity_expected": 50,
                "quantity_received": 50,
                "unit_cost": steel_prod.cost_price
            }],
            notes="Consignment PO-2026-9901 received from Tata Steel",
            user_id=manager_user.id
        )
        await OperationService.validate_receipt(db, rec.id, user_id=manager_user.id)

        # 10. Create a Sample Validated Delivery (-10 Office Chairs)
        chair_prod = next(p for p, _ in products if p.sku == "CHAIR-001")
        deliv = await OperationService.create_delivery(
            db=db,
            org_id=org.id,
            warehouse_id=wh1.id,
            customer_id=customers[0].id,
            items=[{
                "product_id": chair_prod.id,
                "location_id": loc1_1.id,
                "bin_id": bin1.id,
                "quantity_requested": 10,
                "unit_price": chair_prod.selling_price
            }],
            notes="Delivery for L&T On-site Executive Office Furnishing",
            user_id=manager_user.id
        )
        await OperationService.pick_delivery(db, deliv.id, user_id=staff_user.id)
        await OperationService.pack_delivery(db, deliv.id, user_id=staff_user.id)
        await OperationService.validate_delivery(db, deliv.id, user_id=manager_user.id)

        # 11. Create a Sample Internal Transfer (20 Units Steel Rods: Main Store -> Production Floor)
        trf = await OperationService.create_transfer(
            db=db,
            org_id=org.id,
            source_warehouse_id=wh1.id,
            source_location_id=loc1_1.id,
            source_bin_id=bin1.id,
            dest_warehouse_id=wh2.id,
            dest_location_id=loc2_1.id,
            dest_bin_id=bin4.id,
            items=[{"product_id": steel_prod.id, "quantity": 20}],
            notes="Raw materials transfer to fabrication line",
            user_id=manager_user.id
        )
        await OperationService.complete_transfer(db, trf.id, user_id=manager_user.id)

        # 12. Create a Sample Adjustment (3 damaged units of Hex Bolts)
        bolt_prod = next(p for p, _ in products if p.sku == "BOLT-001")
        # Current bolts = 200, Physical = 197
        await OperationService.create_and_apply_adjustment(
            db=db,
            org_id=org.id,
            warehouse_id=wh1.id,
            location_id=loc1_1.id,
            bin_id=bin1.id,
            reason="DAMAGE",
            items=[{"product_id": bolt_prod.id, "physical_quantity": 197}],
            notes="Periodic bin audit: 3 units water damaged during transit",
            user_id=staff_user.id
        )

        # 13. System Notifications
        notif1 = Notification(
            user_id=None,
            notification_type="LOW_STOCK",
            title="Low Stock: Leather Work Gloves",
            message="Only 5 pairs remaining in WH-MAIN. Reorder threshold is 50.",
            link="/inventory/stock"
        )
        notif2 = Notification(
            user_id=None,
            notification_type="OUT_OF_STOCK",
            title="Out of Stock: Measuring Tape 50m",
            message="Zero stock available across all warehouse locations.",
            link="/inventory/stock"
        )
        db.add_all([notif1, notif2])
        await db.commit()

        logger.info("Demo database seeded successfully with 21 products, 3 warehouses, movements, and demo users!")
