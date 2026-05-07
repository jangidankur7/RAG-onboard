"""Interface for RAGIE client operations."""
from typing import Protocol


class IRagieClient(Protocol):
    """Interface for RAGIE client operations."""
    
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
        ...