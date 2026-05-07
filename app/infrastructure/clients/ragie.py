"""Clean RAGIE API client - only RAGIE operations with native async support."""
import os
import logging
from ragie import Ragie
from ragie.models import CreateDocumentParams, File
from injector import inject

from app.interfaces.ragie_client_interface import IRagieClient

logger = logging.getLogger(__name__)

# Environment variables
RAGIE_API_URL = os.getenv("RAGIE_API_URL", "https://api.ragie.ai")


class RagieClient(IRagieClient):
    """RAGIE API client using native async methods."""
    
    @inject
    def __init__(self):
        """Initialize RAGIE client with native async support."""
        self.partition = os.getenv("ENVIRONMENT", "test").lower()
        self.api_key = os.getenv("RAGIE_API_KEY")
        if not self.api_key:
            logger.error("RAGIE_API_KEY environment variable is required")
            raise ValueError("RAGIE_API_KEY environment variable is required")
        
        self.client = Ragie(auth=self.api_key)
    
    async def upload_document_content(
        self,
        content: bytes,
        filename: str,
        asset_id: str,
        document_type: str,
        manufacturer: str,
        model: str
    ) -> str:
        """Upload a document to RAGIE with additional data as metadata."""
        try:
            # Prepare metadata for RAGIE (doc_category instead of document_type which is reserved)
            ragie_metadata = {
                "asset_id": asset_id,
                "doc_category": document_type,
                "manufacturer": manufacturer,
                "model": model,
                "filename": filename
            }
            
            # Create Ragie File object
            ragie_file = File(
                content=content,
                file_name=filename,
                content_type="application/pdf"
            )
            
            # Upload to RAGIE with metadata
            request = CreateDocumentParams(
                file=ragie_file,
                partition=self.partition,
                metadata=ragie_metadata
            )
            response = await self.client.documents.create_async(request=request)
            return response.id            
        except Exception as e:
            logger.error(f"Failed to upload document {filename}: {str(e)}")
            raise