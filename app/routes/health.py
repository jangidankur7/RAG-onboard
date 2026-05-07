"""Health check route for onboarding service."""
from fastapi import APIRouter
from app.models.health import HealthResponse

router = APIRouter(
    prefix="/health",
    tags=["health"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Health check endpoint to verify service status."""
    return HealthResponse(
        message="Assistant Chat Onboarding API is running",
        status="healthy"
    )
