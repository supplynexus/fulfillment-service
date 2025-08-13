"""
API version 1 router
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, customers, orders, products, webhooks, dashboard, health, external_systems, shopify_orders

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(external_systems.router, prefix="/external-systems", tags=["external-systems"])
api_router.include_router(shopify_orders.router, prefix="/shopify", tags=["shopify"])

