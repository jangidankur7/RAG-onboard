"""
Private documents repository interface for dependency injection.
"""
from typing import Protocol, List, Optional


class IPrivateDocumentsRepository(Protocol):
    """Protocol defining the interface for private documents repository operations."""
    
    async def upload_document(
        self, 
        file_path: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a document to the private storage.
        
        Args:
            file_path: Path/key for the document
            content: Document content as bytes
            content_type: MIME type of the content
            metadata: Additional metadata for the document
            
        Returns:
            Full S3 URI of the uploaded document
        """
        ...
    
    async def list_documents(
        self, 
        prefix: Optional[str] = None,
        max_results: Optional[int] = None
    ) -> List[dict]:
        """
        List documents in the private storage.
        
        Args:
            prefix: Optional prefix to filter documents
            max_results: Maximum number of results to return
            
        Returns:
            List of document metadata dictionaries
        """
        ...
    
    async def get_document(
        self, 
        file_path: str
    ) -> Optional[bytes]:
        """
        Get document content from private storage.
        
        Args:
            file_path: Path/key for the document
            
        Returns:
            Document content as bytes, or None if not found
        """
        ...
    
    async def document_exists(
        self, 
        file_path: str
    ) -> bool:
        """
        Check if a document exists in private storage.
        
        Args:
            file_path: Path/key for the document
            
        Returns:
            True if document exists, False otherwise
        """
        ...
    
    async def delete_document(
        self, 
        file_path: str
    ) -> bool:
        """
        Delete a document from private storage.
        
        Args:
            file_path: Path/key for the document
            
        Returns:
            True if deletion was successful
        """
        ...
    
    async def get_document_metadata(
        self, 
        file_path: str
    ) -> Optional[dict]:
        """
        Get document metadata without downloading content.
        
        Args:
            file_path: Path/key for the document
            
        Returns:
            Document metadata dictionary, or None if not found
        """
        ...