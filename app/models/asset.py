"""Asset-related models for onboarding service."""
from typing import Optional, Dict
from pydantic import Field
from fastapi_camelcase import CamelModel

from .enums import AssetStatus
from .document import DocumentInfo


class Asset(CamelModel):
    """Asset model."""
    asset_id: str = Field(..., description="Unique asset identifier")
    manufacturer: str = Field(..., description="Device manufacturer name")
    model: str = Field(..., description="Device model name")
    status: AssetStatus = Field(..., description="Current onboarding status")
    documents: Dict[str, DocumentInfo] = Field(
        default_factory=dict, 
        description="Dictionary of document types to document information"
    )
    onboarding_started_utc: Optional[str] = Field(None, description="ISO 8601 timestamp when onboarding was initiated")
    onboarding_completed_utc: Optional[str] = Field(None, description="ISO 8601 timestamp when onboarding was completed")
    created_utc: str = Field(..., description="ISO 8601 record creation timestamp")
    updated_utc: str = Field(..., description="ISO 8601 last update timestamp")
    created_by: str = Field(..., description="User who initiated the onboarding")
    reviewed_by: Optional[str] = Field(None, description="User who reviewed the asset")

    class Config:
        """Pydantic configuration, to fetch just the ENUM values."""
        use_enum_values = True

