"""
S3 client interface for dependency injection.
"""
from typing import Protocol, List, Optional, AsyncGenerator
from io import BytesIO


class IS3Client(Protocol):
    """Protocol defining the interface for S3 client operations."""
    
    async def list_objects(
        self, 
        bucket_name: str, 
        prefix: Optional[str] = None,
        max_keys: Optional[int] = None
    ) -> List[dict]:
        """
        List objects in an S3 bucket with optional prefix filter.
        
        Args:
            bucket_name: Name of the S3 bucket
            prefix: Optional prefix to filter objects
            max_keys: Maximum number of keys to return
            
        Returns:
            List of object metadata dictionaries
        """
        ...
    
    async def object_exists(
        self, 
        bucket_name: str, 
        key: str
    ) -> bool:
        """
        Check if an object exists in S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            key: Object key/path
            
        Returns:
            True if object exists, False otherwise
        """
        ...
    
    async def get_object(
        self, 
        bucket_name: str, 
        key: str
    ) -> Optional[bytes]:
        """
        Get object content from S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            key: Object key/path
            
        Returns:
            Object content as bytes, or None if not found
        """
        ...
    
    async def get_object_stream(
        self, 
        bucket_name: str, 
        key: str
    ) -> Optional[AsyncGenerator[bytes, None]]:
        """
        Get object content as an async stream from S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            key: Object key/path
            
        Returns:
            Async generator yielding object content chunks, or None if not found
        """
        ...
    
    async def put_object(
        self, 
        bucket_name: str, 
        key: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Upload an object to S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            key: Object key/path
            content: Object content as bytes
            content_type: MIME type of the content
            metadata: Additional metadata for the object
            
        Returns:
            True if upload was successful
        """
        ...
    
    async def delete_object(
        self, 
        bucket_name: str, 
        key: str
    ) -> bool:
        """
        Delete an object from S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            key: Object key/path
            
        Returns:
            True if deletion was successful
        """
        ...
    
    async def get_object_metadata(
        self, 
        bucket_name: str, 
        key: str
    ) -> Optional[dict]:
        """
        Get object metadata from S3 without downloading content.
        
        Args:
            bucket_name: Name of the S3 bucket
            key: Object key/path
            
        Returns:
            Object metadata dictionary, or None if not found
        """
        ...