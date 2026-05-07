"""Interface for document processing service operations."""
from typing import Protocol
from app.models.asset import Asset


class IDocumentProcessingService(Protocol):
    """Interface for document processing service - business logic layer."""
    
    async def process_asset_document(self, asset: Asset, document_type: str) -> None:
        """Process a single document from CDN: move to private S3, generate metadata, and ingest to RAGIE."""
        ...