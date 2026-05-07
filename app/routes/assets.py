"""Asset management routes for onboarding service."""
from fastapi import APIRouter, Query, File, UploadFile, Form
from fastapi_injector import Injected
from typing import List, Optional, Union, Annotated
import logging

logger = logging.getLogger(__name__)
from app.interfaces.asset_onboarding_service_interface import IAssetOnboardingService
from app.models.asset import Asset
from app.models.onboard import OnboardingInitRequest, OnboardingInitResponse, OnboardingConfirmResponse

# Define the API router for asset management
# Exceptions are handled globally via exception handlers
router = APIRouter(
    prefix="/assets",
    tags=["assets"],
    responses={404: {"description": "Not found"}},
)

@router.get("/search", response_model=Asset)
async def search_assets(
    manufacturer: str = Query(..., description="Device manufacturer name"),
    model: str = Query(..., description="Device model name"),
    onboarding_service: IAssetOnboardingService = Injected(IAssetOnboardingService)
) -> Asset:
    """
    Search for existing asset by manufacturer and model.
    
    Returns:
        200 - Search results with public asset data if exists
        404 - Asset not found
        500 - Search failed
    """
    asset = await onboarding_service.search_asset(manufacturer, model)
    return asset
    

@router.post("/onboard/init", response_model=OnboardingInitResponse, status_code=202)
async def initialize_onboarding(
    request: OnboardingInitRequest,
    onboarding_service: IAssetOnboardingService = Injected(IAssetOnboardingService)
) -> OnboardingInitResponse:
    """
    Initialize automated asset onboarding with web scraping.
    
    Body: manufacturer, model
    
    Returns:
        202 - Onboarding initiated, returns asset_id
        409 - Asset already exists
    """
    # TODO: Get from authentication context
    user_id = "system"      
    return await onboarding_service.initialize_onboarding(
        request.manufacturer, 
        request.model, 
        user_id
    )


@router.delete("/onboard/{asset_id}/cancel", status_code=204)
async def cancel_onboarding(
    asset_id: str,
    onboarding_service: IAssetOnboardingService = Injected(IAssetOnboardingService)
):
    """
    Cancel asset onboarding process.
    
    Returns:
        204 - Onboarding cancelled
        400 - Cannot cancel (wrong status)
        404 - Asset not found
    """
    await onboarding_service.cancel_onboarding(asset_id)


@router.post("/onboard/{asset_id}", response_model=OnboardingConfirmResponse, status_code=202)
async def confirm_documents_and_start_processing(
    asset_id: str,
    onboarding_service: IAssetOnboardingService = Injected(IAssetOnboardingService),
    document_overrides: Optional[str] = Form(None, description="JSON string of document type to filename mappings"),
    files: Annotated[List[Union[UploadFile, str]], File(description="PDF document files to upload (only .pdf files accepted)")] = []
) -> OnboardingConfirmResponse:
    """
    Confirm documents after user review and start OCR/ingestion.
    
    Supports multipart/form-data with:
    - document_overrides: JSON string mapping document types to filenames
    - files: List of PDF document files to upload (only .pdf files accepted)
    
    User-provided documents will override auto-sourced ones.
    
    Returns:
        202 - OCR/ingestion started, status "processing"
        400 - Invalid request or wrong asset status
        404 - Asset not found
    """
    # TODO: Get from authentication context
    user_id = "system"
    
    return await onboarding_service.confirm_documents_and_start_processing(
        asset_id, 
        user_id,
        document_overrides,
        files
    )


@router.get("/{asset_id}", response_model=Asset)
async def get_asset(
    asset_id: str,
    onboarding_service: IAssetOnboardingService = Injected(IAssetOnboardingService)
) -> Asset:
    """
    Retrieve asset information and onboarding status.
    
    Returns:
        200 - Asset object with current status and document details
        404 - Asset not found
    """
    return await onboarding_service.get_asset(asset_id)
