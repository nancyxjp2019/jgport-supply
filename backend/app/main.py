from fastapi import APIRouter, FastAPI

from app.api.error_handlers import register_exception_handlers
from app.api.routers import access, audit_logs, contracts, funds, health, inventory, mini_auth, orders, reports, system_configs
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="6.0.0",
    debug=settings.debug,
)
register_exception_handlers(app)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(access.router)
api_router.include_router(mini_auth.router)
api_router.include_router(system_configs.router)
api_router.include_router(audit_logs.router)
api_router.include_router(contracts.router)
api_router.include_router(orders.router)
api_router.include_router(funds.router)
api_router.include_router(inventory.router)
api_router.include_router(reports.router)
app.include_router(api_router, prefix=settings.api_prefix)
