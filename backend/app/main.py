from fastapi import APIRouter, FastAPI

from app.api.routers import health
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="6.0.0",
    debug=settings.debug,
)

api_router = APIRouter()
api_router.include_router(health.router)
app.include_router(api_router, prefix=settings.api_prefix)
