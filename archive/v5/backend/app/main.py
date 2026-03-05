from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.middlewares import ApiRateLimitMiddleware, RequestContextMiddleware, SecurityHeadersMiddleware
from app.api.routers import (
    admin_agreement_templates,
    admin_auth,
    admin_logs,
    admin_master_data,
    admin_users,
    auth,
    files,
    health,
    v5_dashboard,
    v5_contracts,
    v5_inventory,
    v5_purchase_orders,
    v5_reports,
    v5_reference,
    v5_sales_orders,
)
from app.core.config import get_settings
from app.core.logging_config import get_system_logger, setup_logging
from app.db.init_db import init_db

settings = get_settings()
setup_logging()
system_logger = get_system_logger()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ApiRateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)

if settings.file_storage_backend == "local":
    upload_dir = Path(settings.local_upload_dir).expanduser()
    if not upload_dir.is_absolute():
        upload_dir = Path(__file__).resolve().parents[1] / upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.local_upload_base_url,
        StaticFiles(directory=str(upload_dir)),
        name="uploaded-files",
    )

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admin_auth.router)
api_router.include_router(admin_agreement_templates.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_logs.router)
api_router.include_router(admin_master_data.router)
api_router.include_router(files.router)
api_router.include_router(v5_dashboard.router)
api_router.include_router(v5_reference.router)
api_router.include_router(v5_contracts.router)
api_router.include_router(v5_inventory.router)
api_router.include_router(v5_reports.router)
api_router.include_router(v5_sales_orders.router)
api_router.include_router(v5_purchase_orders.router)

app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    system_logger.info(
        "应用启动完成",
        extra={
            "env": settings.env,
            "api_prefix": settings.api_prefix,
        },
    )


@app.on_event("shutdown")
def on_shutdown() -> None:
    system_logger.info("应用已停止")
