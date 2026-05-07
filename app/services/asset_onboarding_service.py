"""Comprehensive asset onboarding service."""
import logging
import uuid
import asyncio
import hashlib
from typing import List, Optional, Dict, Tuple, Union
from fastapi import UploadFile
from datetime import datetime, timedelta
from injector import inject

from app.interfaces.asset_repository_interface import IAssetRepository
from app.interfaces.document_search_service_interface import IDocumentSearchService
from app.interfaces.private_documents_repository_interface import IPrivateDocumentsRepository
from app.interfaces.web_search_interface import IWebSearchClient
from app.interfaces.date_provider_interface import IDateProvider
from app.interfaces.asset_onboarding_service_interface import IAssetOnboardingService
from app.interfaces.document_processing_service_interface import IDocumentProcessingService
from app.utils.checksum import calculate_checksum
from app.models.asset import Asset
from app.models.document import DocumentInfo
from app.models.onboard import OnboardingInitResponse, OnboardingConfirmResponse
from app.models.enums import AssetStatus, DocumentStatus, DocumentSource
from app.models.excpetions import (
    AssetAlreadyExistsException,
    AssetNotFoundException,
    AssetInvalidStatusException,
)

logger = logging.getLogger(__name__)


class AssetOnboardingService(IAssetOnboardingService):
    """Comprehensive asset onboarding service managing the full workflow."""
    
    @inject
    def __init__(
        self,
        asset_repository: IAssetRepository,
        document_search_service: IDocumentSearchService,
        document_storage: IPrivateDocumentsRepository,
        web_search_client: IWebSearchClient,
        date_provider: IDateProvider,
        document_processing_service: IDocumentProcessingService
    ):
        """Initialize asset onboarding service."""
        self.asset_repository = asset_repository
        self.document_search_service = document_search_service
        self.document_storage = document_storage
        self.web_search_client = web_search_client  # For verify_pdf and download_pdf operations
        self.date_provider = date_provider
        self.document_processing_service = document_processing_service

    # Public interface methods
    
    async def search_asset(self, manufacturer: str, model: str) -> Optional[Asset]:
        """Search for existing asset by manufacturer and model."""
        asset = await self.asset_repository.search_by_manufacturer_model(manufacturer, model)
        if not asset or self._is_search_stuck(asset):
            raise AssetNotFoundException(f"{manufacturer} {model}")
        return asset

    async def initialize_onboarding(self, manufacturer: str, model: str, user_id: str) -> OnboardingInitResponse:
        """Initialize automated asset onboarding with web scraping."""
        try:
            # Check if asset already exists
            asset = await self.asset_repository.search_by_manufacturer_model(manufacturer, model)
            if not asset:
                now = self.date_provider.utc_now().isoformat()
                asset = Asset(
                    asset_id=str(uuid.uuid4()),
                    manufacturer=manufacturer,
                    model=model,
                    status=AssetStatus.SEARCHING,
                    documents={},
                    onboarding_started_utc=now,
                    created_utc=now,
                    updated_utc=now,
                    created_by=user_id
                )
                await self.asset_repository.upsert(asset)
                # The document sourcing will be done in background
                # Client will poll for status updates
                asyncio.create_task(self._perform_automated_search_background(asset))
            elif asset.status == AssetStatus.FAILED or self._is_search_stuck(asset):
                # Retry sourcing
                asyncio.create_task(self._perform_automated_search_background(asset))
            else:
                raise AssetAlreadyExistsException(manufacturer, model, asset.status)

            return OnboardingInitResponse(
                asset_id=asset.asset_id,
                status=asset.status,
            ) 
        except Exception as e:
            logger.error(f"Failed to initialize onboarding: {str(e)}")
            raise

    async def cancel_onboarding(self, asset_id: str) -> None:
        """Cancel asset onboarding process."""
        try:
            asset = await self.asset_repository.get_by_id(asset_id)
            if not asset:
                raise AssetNotFoundException(asset_id)

            # Check if asset onboarding can be cancelled
            if asset.status != AssetStatus.USER_REVIEW and not self._is_search_stuck(asset):
                raise AssetInvalidStatusException(
                    current_status=asset.status,
                    operation="cancel onboarding",
                    allowed_statuses=["user_review", "searching (when stuck)"]
                )

            # Delete the asset to avoid the lookups for cancelled assets
            await self.asset_repository.delete(asset_id)
            
        except Exception as e:
            logger.error(f"Failed to cancel onboarding: {str(e)}")
            raise

    async def confirm_documents_and_start_processing(
        self, 
        asset_id: str, 
        user_id: str,
        document_overrides: Optional[str] = None,
        files: List[Union[UploadFile, str]] = []
    ) -> OnboardingConfirmResponse:
        """Confirm documents after user review and start OCR/ingestion."""
        
        asset = await self.asset_repository.get_by_id(asset_id)
        if not asset:
            raise AssetNotFoundException(asset_id)
        
        if asset.status != AssetStatus.USER_REVIEW:
            raise AssetInvalidStatusException(
                current_status=asset.status,
                operation="confirm documents",
                allowed_statuses=["user_review"]
            )
        
        # Filter files - only accept valid PDF files
        valid_files = []
        for file in files:
            # Check if it's a PDF file
            try:
                if file.filename and file.filename.strip().lower().endswith('.pdf'):
                    valid_files.append(file)
            except AttributeError:
                # Skip objects without filename attribute (like strings)
                pass
        # Pre-process uploaded files (read content before background task)
        user_documents = None
        if valid_files and document_overrides:
            user_documents = await self._process_uploaded_documents(document_overrides, valid_files)
        
        # Update status to PROCESSING immediately
        asset.status = AssetStatus.PROCESSING
        asset.updated_utc = self.date_provider.utc_now().isoformat()        
        updated_asset = await self.asset_repository.upsert(asset)
        
        # Start background processing without awaiting (with pre-processed document data)
        asyncio.create_task(
            self._process_asset_documents_background(
                updated_asset, user_documents
            )
        )        
        return OnboardingConfirmResponse(
            asset_id=asset_id,
            status=asset.status,
        )
        
    async def get_asset(self, asset_id: str) -> Asset:
        """Retrieve public asset information."""
        asset = await self.asset_repository.get_by_id(asset_id)
        if not asset:
            raise AssetNotFoundException(asset_id)
        return asset

    # Internal helper methods

    def _is_search_stuck(self, asset: Asset) -> bool:
        return asset.status == AssetStatus.SEARCHING and \
               datetime.fromisoformat(asset.updated_utc) < (self.date_provider.utc_now() - timedelta(minutes=5))
    
    async def _perform_automated_search_background(self, asset: Asset) -> Asset:
        """Internal method to perform automated document search.
            1. Searches for all required documents using document search service
            2. Updates asset status to USER_REVIEW with the document links  
            3. If any step fails, deletes the asset to avoid stale entries
        """
        try:
            # Search for documents using document search service
            # The document search service handles everything: search, verify, download, CDN upload
            documents = await self.document_search_service.search_device_documentation(
                asset.manufacturer, asset.model
            )
            
            # Update asset with found documents
            asset.documents = documents
            asset.status = AssetStatus.USER_REVIEW
            asset.updated_utc = self.date_provider.utc_now().isoformat()
            
            # Save updated asset
            updated_asset = await self.asset_repository.upsert(asset)
            
            logger.info(f"Automated search completed for {asset.asset_id}, found {len(documents)} documents")
            return updated_asset            
        except Exception as e:
            logger.error(f"Failed automated search for {asset.asset_id}: {str(e)}; cleaning up asset.")
            await self.asset_repository.delete(asset.asset_id)
            raise

    async def _process_asset_documents_background(
        self, 
        asset: Asset, 
        user_documents: Optional[Dict[str, Tuple[bytes, str]]] = None
    ) -> None:
        """Process confirmed documents by delegating to document processing service."""
        try:
            # Process user-provided document overrides first
            if user_documents:
                try:
                    await self._handle_user_document_overrides(asset, user_documents)
                    # Update asset with user documents
                    asset = await self.asset_repository.upsert(asset)
                except Exception as e:
                    logger.error(f"Failed to process user document overrides for asset {asset.asset_id}: {e}")
                    # Continue with auto-sourced documents even if user overrides fail
            
            successful_documents = 0
            
            # Process each document using the document processing service
            for doc_type in asset.documents.keys():
                try:
                    await self.document_processing_service.process_asset_document(asset, doc_type)
                    successful_documents += 1
                except Exception as e:
                    logger.error(f"Failed to process document {doc_type} for asset {asset.asset_id}: {e}")
                    asset.documents[doc_type].status = DocumentStatus.FAILED
            
            # Determine final asset status based on processing results
            if successful_documents == 0:
                asset.status = AssetStatus.FAILED
            else:
                asset.status = AssetStatus.INTERNAL_REVIEW

            # Update asset with final status
            asset.updated_utc = self.date_provider.utc_now().isoformat()
            await self.asset_repository.upsert(asset)
            
            logger.info(f"Background processing completed for asset: {asset.asset_id} ({successful_documents}/{len(asset.documents)} successful)")
            
        except Exception as e:
            logger.error(f"Background processing failed for asset {asset.asset_id}: {e}")
            asset.status = AssetStatus.FAILED
            asset.updated_utc = self.date_provider.utc_now().isoformat()
            await self.asset_repository.upsert(asset)

    async def _process_uploaded_documents(
        self, 
        document_overrides: str, 
        files: List[UploadFile]
    ) -> Dict[str, Tuple[bytes, str]]:
        """Process uploaded files and document override mapping."""
        import json
        
        try:
            override_mapping = json.loads(document_overrides)
            user_documents: Dict[str, Tuple[bytes, str]] = {}
            
            for file in files:
                if file.filename and file.filename in override_mapping.values():
                    # Find document type for this filename
                    doc_type = next(
                        (doc_type for doc_type, filename in override_mapping.items() 
                         if filename == file.filename), 
                        None
                    )
                    if doc_type:
                        content = await file.read()
                        # Store both content and original filename
                        user_documents[doc_type] = (content, file.filename)
            return user_documents
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid document_overrides JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to process uploaded documents: {e}")
            return {}

    async def _handle_user_document_overrides(
        self, 
        asset: Asset, 
        user_documents: Dict[str, Tuple[bytes, str]]
    ) -> None:
        """Handle user-provided document overrides by uploading to private storage."""
        try:
            for doc_type, (document_content, original_filename) in user_documents.items():
                try:
                    # Generate file details using original filename
                    checksum = calculate_checksum(document_content)
                    file_size_kb = len(document_content) // 1024
                    private_s3_key = f"assets/{asset.asset_id}/documents/{doc_type}/{original_filename}"
                    
                    # Upload to private storage
                    s3_uri = await self.document_storage.upload_document(
                        file_path=private_s3_key,
                        content=document_content,
                        content_type="application/pdf",
                        metadata={
                            "asset_id": asset.asset_id,
                            "document_type": doc_type,
                            "source": "user",
                            "uploaded_by": "user"  # TODO: Use actual user ID
                        }
                    )
                    
                    # Create or update document info (user documents override auto-sourced ones)
                    doc_info = DocumentInfo(
                        source=DocumentSource.USER,
                        status=DocumentStatus.PENDING,
                        s3_key=s3_uri,  # Store full S3 URI
                        preview_url=None,  # Will be generated during processing
                        file_name=original_filename,  # Use original filename
                        language="en",
                        page_count=None,  # Will be determined during OCR
                        file_size_kb=file_size_kb,
                        confidence=None,  # User documents have implicit high confidence
                        source_url=None,
                        checksum=checksum,
                        ingestion_id=None
                    )
                    
                    # Override existing document or add new one
                    asset.documents[doc_type] = doc_info
                except Exception as e:
                    logger.error(f"Failed to process user document for {doc_type}: {e}")
                    # Continue processing other documents even if one fails
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to handle user document overrides for asset {asset.asset_id}: {e}")
            raise

    
