from fastapi import APIRouter
from src.models import HTTPSuccess


health_router = APIRouter()


@health_router.get("/health")
async def health():
    return HTTPSuccess()
