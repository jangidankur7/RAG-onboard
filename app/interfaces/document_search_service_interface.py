"""Interface for document search service operations."""
from typing import Protocol, Dict

from app.models.document import DocumentInfo
from app.models.enums import DocumentType


class IDocumentSearchService(Protocol):
    """Interface for document search service - business logic layer."""
    
    async def search_device_documentation(
        self,
        manufacturer: str,
        model: str
    ) -> Dict[DocumentType, DocumentInfo]:
        """Search for device documentation with intelligent filtering and return ready-to-use DocumentInfo objects."""
        ...

