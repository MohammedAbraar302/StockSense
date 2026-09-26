from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.locations import router as locations_router
from app.api.v1.products import router as products_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.operations import router as operations_router
from app.api.v1.reconciliation import router as reconciliation_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.audit import router as audit_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(locations_router)
api_v1_router.include_router(products_router)
api_v1_router.include_router(inventory_router)
api_v1_router.include_router(operations_router)
api_v1_router.include_router(reconciliation_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(audit_router)
