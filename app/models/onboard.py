"""Onboard-related models for onboarding service."""
from typing import Optional, List, Dict
from pydantic import Field
from fastapi_camelcase import CamelModel

class OnboardingInitRequest(CamelModel):
    """Request to initialize asset onboarding."""
    manufacturer: str = Field(..., description="Device manufacturer")
    model: str = Field(..., description="Device model")


class OnboardingInitResponse(CamelModel):
    """Response for onboarding initialization."""
    asset_id: str = Field(..., description="Created asset ID")
    status: str = Field(..., description="Initial status")


class OnboardingConfirmResponse(CamelModel):
    """Response for document confirmation and processing start."""
    asset_id: str = Field(..., description="Asset identifier")
    status: str = Field(..., description="Updated status")


class OnboardingCancelResponse(CamelModel):
    """Response for canceling onboarding."""
    asset_id: str = Field(..., description="Asset ID")
    message: str = Field(..., description="Cancellation message")
