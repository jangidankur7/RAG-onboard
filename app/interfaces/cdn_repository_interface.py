"""
CDN repository interface for dependency injection.
"""
from typing import Protocol, List, Optional


class ICDNRepository(Protocol):
    """Protocol defining the interface for CDN repository operations."""
    
    async def upload_file(
        self, 
        file_path: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to CDN storage.
        
        Args:
            file_path: Path/key for the file
            content: File content as bytes
            content_type: MIME type of the content
            metadata: Additional metadata for the file
            
        Returns:
            CDN URL for the uploaded file
        """
        ...
    
    async def list_files(
        self, 
        prefix: Optional[str] = None,
        max_results: Optional[int] = None
    ) -> List[dict]:
        """
        List files in CDN storage.
        
        Args:
            prefix: Optional prefix to filter files
            max_results: Maximum number of results to return
            
        Returns:
            List of file metadata dictionaries with CDN URLs
        """
        ...
    
    async def get_file_url(
        self, 
        file_path: str
    ) -> Optional[str]:
        """
        Get CDN URL for a file.
        
        Args:
            file_path: Path/key for the file
            
        Returns:
            CDN URL for the file, or None if not found
        """
        ...
    
    async def file_exists(
        self, 
        file_path: str
    ) -> bool:
        """
        Check if a file exists in CDN storage.
        
        Args:
            file_path: Path/key for the file
            
        Returns:
            True if file exists, False otherwise
        """
        ...
    
    async def delete_file(
        self, 
        file_path: str
    ) -> bool:
        """
        Delete a file from CDN storage.
        
        Args:
            file_path: Path/key for the file
            
        Returns:
            True if deletion was successful
        """
        ...
    
    async def get_file_metadata(
        self, 
        file_path: str
    ) -> Optional[dict]:
        """
        Get file metadata without downloading content.
        
        Args:
            file_path: Path/key for the file
            
        Returns:
            File metadata dictionary with CDN URL, or None if not found
        """
        ...

    async def get_file_content(
        self, 
        file_path_or_url: str
    ) -> Optional[bytes]:
        """
        Get file content from CDN storage.
        
        Args:
            file_path_or_url: File path/key or full CDN URL
            
        Returns:
            File content as bytes, or None if not found
        """
        ...