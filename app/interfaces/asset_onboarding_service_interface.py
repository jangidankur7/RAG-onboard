"""Interface for asset onboarding service."""
from typing import Protocol, Optional, List, Union
from fastapi import UploadFile
from app.models.asset import Asset
from app.models.onboard import OnboardingInitResponse, OnboardingConfirmResponse


class IAssetOnboardingService(Protocol):
    """Interface for asset onboarding service operations."""
    
    async def search_asset(self, manufacturer: str, model: str) -> Optional[Asset]:
        """Search for existing asset by manufacturer and model."""
        ...
    
    async def initialize_onboarding(self, manufacturer: str, model: str, user_id: str) -> OnboardingInitResponse:
        """Initialize automated asset onboarding with web scraping."""
        ...
    
    async def cancel_onboarding(self, asset_id: str) -> None:
        """Cancel asset onboarding process."""
        ...
    
    async def confirm_documents_and_start_processing(
        self, 
        asset_id: str, 
        user_id: str,
        document_overrides: Optional[str] = None,
        files: List[Union[UploadFile, str]] = []
    ) -> OnboardingConfirmResponse:
        """Confirm documents after user review and start OCR/ingestion."""
        ...
    
    async def get_asset(self, asset_id: str) -> Asset:
        """Retrieve asset information."""
        ...