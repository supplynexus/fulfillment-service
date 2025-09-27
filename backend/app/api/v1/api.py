"""
API version 1 router
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    customers,
    orders,
    products,
    webhooks,
    dashboard,
    health,
    external_systems,
    shopify_orders,
    shopify_orders_crud,
    shopify_products,
    shopify_stores,
    sync_configs,
    sync_status,
    system,
    scm_orders,
    order_routing,
    routing_rules,
    printify_orders,
    order_automation,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(
    external_systems.router, prefix="/external-systems", tags=["external-systems"]
)
api_router.include_router(sync_status.router, prefix="/sync", tags=["sync"])
api_router.include_router(shopify_orders.router, prefix="/shopify", tags=["shopify"])
api_router.include_router(shopify_orders_crud.router, prefix="/shopify-orders", tags=["shopify-orders-crud"])
api_router.include_router(
    shopify_products.router, prefix="/external-systems", tags=["shopify-products"]
)
api_router.include_router(
    shopify_stores.router, prefix="/shopify", tags=["shopify-stores"]
)
api_router.include_router(
    sync_configs.router, prefix="/sync-configs", tags=["sync-configs"]
)

# SCM Order Management
api_router.include_router(scm_orders.router, prefix="/scm-orders", tags=["scm-orders"])
api_router.include_router(
    order_routing.router, prefix="/routing", tags=["order-routing"]
)
api_router.include_router(
    routing_rules.router, prefix="/routing-rules", tags=["routing-rules"]
)

api_router.include_router(system.router, prefix="/system", tags=["system"])

# Printify Integration
api_router.include_router(printify_orders.router, prefix="/printify", tags=["printify"])

# Order Automation
api_router.include_router(
    order_automation.router, prefix="/automation", tags=["order-automation"]
)
