import os
from typing import List, Optional
from app.interfaces.s3_client_interface import IS3Client
from app.interfaces.ssm_client_interface import ISSMClient
from app.interfaces.memory_cache_interface import IMemoryCache
import logging

logger = logging.getLogger(__name__)


class CDNRepository:
    """Repository for managing CDN files in S3 with CloudFront URLs."""
    
    DISTRIBUTION_DOMAIN_CACHE_KEY = "cdn_distribution_domain"
    CACHE_TTL_HOURS = 24  # Cache for 24 hours
    
    def __init__(self, s3_client: IS3Client, ssm_client: ISSMClient, memory_cache: IMemoryCache):
        """
        Initialize CDN repository.
        
        Args:
            s3_client: Injected S3 client
            ssm_client: Injected SSM client
            memory_cache: Injected memory cache
        """
        self._s3_client = s3_client
        self._ssm_client = ssm_client
        self._memory_cache = memory_cache
        environment = os.getenv('ENVIRONMENT', 'test')
        self._bucket_name = f'arkim-chat-cdn-{environment}'

    async def _get_cdn_domain(self) -> str:
        """
        Get CDN distribution domain from cache or SSM Parameter Store.
        
        Returns:
            CDN distribution domain with proper protocol
        """
        # Try to get from cache first
        cached_domain = self._memory_cache.get(self.DISTRIBUTION_DOMAIN_CACHE_KEY)
        if cached_domain:
            return cached_domain
        
        # Fetch from SSM Parameter Store
        domain = await self._ssm_client.get_parameter("/chat/shared/distributionDomainName", decrypt=False)
        if not domain:
            raise ValueError("CDN distribution domain not found in SSM Parameter Store")
        
        # Ensure domain has proper protocol
        if not domain.startswith(('http://', 'https://')):
            domain = f"https://{domain}"
        
        # Cache the domain for future use
        self._memory_cache.set(
            self.DISTRIBUTION_DOMAIN_CACHE_KEY, 
            domain, 
            ttl_seconds=self.CACHE_TTL_HOURS * 3600
        )
        
        return domain

    async def _get_cdn_url(self, file_path: str) -> str:
        """
        Convert S3 path to CloudFront URL.
        
        Args:
            file_path: S3 object key
            
        Returns:
            CloudFront URL for the file
        """
        # S3 client already normalizes the key, but we need to handle it here for URL generation
        clean_path = file_path.lstrip('/')
        cdn_domain = await self._get_cdn_domain()
        return f"{cdn_domain}/{clean_path}"

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
        try:
            success = await self._s3_client.put_object(
                bucket_name=self._bucket_name,
                key=file_path,
                content=content,
                content_type=content_type,
                metadata=metadata
            )
            
            if not success:
                raise RuntimeError(f"Failed to upload file {file_path}")
            
            cdn_url = await self._get_cdn_url(file_path)
            
            return cdn_url
            
        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {e}")
            raise

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
        try:
            objects = await self._s3_client.list_objects(
                bucket_name=self._bucket_name,
                prefix=prefix,
                max_keys=max_results
            )
            
            # Transform S3 object metadata to file metadata with CDN URLs
            files = []
            for obj in objects:
                cdn_url = await self._get_cdn_url(obj['key'])
                files.append({
                    'path': obj['key'],
                    'cdn_url': cdn_url,
                    'size': obj['size'],
                    'last_modified': obj['last_modified'],
                    'etag': obj['etag'],
                    'storage_class': obj['storage_class']
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files with prefix {prefix}: {e}")
            raise

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
        try:
            exists = await self._s3_client.object_exists(
                bucket_name=self._bucket_name,
                key=file_path
            )
            
            if exists:
                cdn_url = await self._get_cdn_url(file_path)
                return cdn_url
            
            logger.warning(f"File not found: {file_path}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get file URL {file_path}: {e}")
            raise

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
        try:
            exists = await self._s3_client.object_exists(
                bucket_name=self._bucket_name,
                key=file_path
            )
            return exists
            
        except Exception as e:
            logger.error(f"Failed to check file existence {file_path}: {e}")
            raise

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
        try:
            success = await self._s3_client.delete_object(
                bucket_name=self._bucket_name,
                key=file_path
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            raise

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
        try:
            metadata = await self._s3_client.get_object_metadata(
                bucket_name=self._bucket_name,
                key=file_path
            )
            
            if metadata:
                # Transform S3 metadata to file metadata with CDN URL
                cdn_url = await self._get_cdn_url(metadata['key'])
                file_metadata = {
                    'path': metadata['key'],
                    'cdn_url': cdn_url,
                    'size': metadata['size'],
                    'last_modified': metadata['last_modified'],
                    'etag': metadata['etag'],
                    'content_type': metadata['content_type'],
                    'metadata': metadata['metadata']
                }
                
                return file_metadata
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get file metadata {file_path}: {e}")
            raise

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
        try:
            # Extract file path from CDN URL if needed
            file_path = await self._extract_file_path_from_url(file_path_or_url)
            
            content = await self._s3_client.get_object(
                bucket_name=self._bucket_name,
                key=file_path
            )
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to get file content {file_path_or_url}: {e}")
            return None

    async def _extract_file_path_from_url(self, file_path_or_url: str) -> str:
        """Extract file path from CDN URL or return as-is if already a path."""
        # Check if it's a full URL
        if file_path_or_url.startswith('http'):
            cdn_domain = await self._get_cdn_domain()
            if cdn_domain in file_path_or_url:
                from urllib.parse import urlparse
                parsed_url = urlparse(file_path_or_url)
                return parsed_url.path.lstrip('/')
        
        # If it's not a URL or not our CDN, treat as file path
        return file_path_or_url