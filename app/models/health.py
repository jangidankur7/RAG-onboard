from pydantic import Field
from fastapi_camelcase import CamelModel
from datetime import datetime

class HealthResponse(CamelModel):
    """Response model for health check endpoint"""
    message: str = Field(..., description="Health status message")
    status: str = Field(default="healthy", description="Service status")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Response timestamp")
