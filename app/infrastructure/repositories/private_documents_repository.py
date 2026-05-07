import os
from typing import List, Optional
from app.interfaces.s3_client_interface import IS3Client
import logging

logger = logging.getLogger(__name__)


class PrivateDocumentsRepository:
    """Repository for managing private documents in S3."""
    
    def __init__(self, s3_client: IS3Client):
        """
        Initialize private documents repository.
        
        Args:
            s3_client: Injected S3 client
        """
        self._s3_client = s3_client
        environment = os.getenv('ENVIRONMENT', 'test')
        self._bucket_name = f'arkim-chat-onboarding-data-{environment}'

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
        try:
            success = await self._s3_client.put_object(
                bucket_name=self._bucket_name,
                key=file_path,
                content=content,
                content_type=content_type,
                metadata=metadata
            )
            
            if not success:
                raise RuntimeError(f"Failed to upload document {file_path}")
            
            # Return full S3 URI
            return self._get_full_s3_uri(file_path)
            
        except Exception as e:
            logger.error(f"Failed to upload document {file_path}: {e}")
            raise

    def _get_full_s3_uri(self, s3_key: str) -> str:
        """Convert S3 key to full S3 URI."""
        # Remove s3:// prefix if already present
        if s3_key.startswith('s3://'):
            return s3_key
        
        # Remove leading slash if present
        clean_key = s3_key.lstrip('/')
        
        return f"s3://{self._bucket_name}/{clean_key}"

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
        try:
            objects = await self._s3_client.list_objects(
                bucket_name=self._bucket_name,
                prefix=prefix,
                max_keys=max_results
            )
            
            # Transform S3 object metadata to document metadata
            documents = []
            for obj in objects:
                documents.append({
                    'path': obj['key'],
                    'size': obj['size'],
                    'last_modified': obj['last_modified'],
                    'etag': obj['etag'],
                    'storage_class': obj['storage_class']
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list documents with prefix {prefix}: {e}")
            raise

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
        try:
            content = await self._s3_client.get_object(
                bucket_name=self._bucket_name,
                key=file_path
            )
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to get document {file_path}: {e}")
            raise

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
        try:
            exists = await self._s3_client.object_exists(
                bucket_name=self._bucket_name,
                key=file_path
            )
            return exists
            
        except Exception as e:
            logger.error(f"Failed to check document existence {file_path}: {e}")
            raise

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
        try:
            success = await self._s3_client.delete_object(
                bucket_name=self._bucket_name,
                key=file_path
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete document {file_path}: {e}")
            raise

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
        try:
            metadata = await self._s3_client.get_object_metadata(
                bucket_name=self._bucket_name,
                key=file_path
            )
            
            if metadata:
                # Transform S3 metadata to document metadata
                doc_metadata = {
                    'path': metadata['key'],
                    'size': metadata['size'],
                    'last_modified': metadata['last_modified'],
                    'etag': metadata['etag'],
                    'content_type': metadata['content_type'],
                    'metadata': metadata['metadata']
                }
                
                return doc_metadata
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document metadata {file_path}: {e}")
            raise