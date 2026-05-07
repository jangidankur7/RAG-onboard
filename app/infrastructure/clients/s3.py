import aioboto3
from typing import List, Optional, AsyncGenerator
from botocore.exceptions import ClientError, NoCredentialsError
import logging
import os

logger = logging.getLogger(__name__)


class S3Client:
    """S3 client with async operations."""
    
    REGION = "us-west-2"
    
    def __init__(self):
        """Initialize S3 client."""
        self.region_name = self.REGION
        environment = os.getenv("ENVIRONMENT", "test")
        self.bucket_name = f"chat-onboarding-data-{environment}"
        self._session = None

    def _normalize_key(self, key: str) -> str:
        """
        Normalize S3 object key by removing leading slashes.
        
        Args:
            key: Raw object key/path
            
        Returns:
            Normalized key without leading slashes
        """
        return key.lstrip('/')

    async def _get_session(self):
        """Get or create aioboto3 session."""
        if self._session is None:
            self._session = aioboto3.Session()
        return self._session

    async def _get_client(self):
        """Get S3 client from session."""
        session = await self._get_session()
        return session.client('s3', region_name=self.region_name)

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
        try:
            async with await self._get_client() as s3:
                params = {
                    'Bucket': bucket_name
                }
                
                if prefix:
                    params['Prefix'] = self._normalize_key(prefix)
                if max_keys:
                    params['MaxKeys'] = max_keys
                
                response = await s3.list_objects_v2(**params)
                
                contents = response.get('Contents', [])
                
                # Format the response to include useful metadata
                objects = []
                for obj in contents:
                    objects.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'etag': obj['ETag'].strip('"'),
                        'storage_class': obj.get('StorageClass', 'STANDARD')
                    })
                
                return objects
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                logger.error(f"Bucket {bucket_name} does not exist")
                return []
            else:
                logger.error(f"Error listing objects in {bucket_name}: {e}")
                raise
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing objects: {e}")
            raise

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
        try:
            normalized_key = self._normalize_key(key)
            async with await self._get_client() as s3:
                await s3.head_object(Bucket=bucket_name, Key=normalized_key)
                return True
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            else:
                logger.error(f"Error checking if object exists s3://{bucket_name}/{key}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error checking object existence: {e}")
            raise

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
        try:
            normalized_key = self._normalize_key(key)
            async with await self._get_client() as s3:
                response = await s3.get_object(Bucket=bucket_name, Key=normalized_key)
                
                # Read the body content
                async with response['Body'] as stream:
                    content = await stream.read()
                
                return content
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(f"Object not found: s3://{bucket_name}/{key}")
                return None
            else:
                logger.error(f"Error getting object s3://{bucket_name}/{key}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error getting object: {e}")
            raise

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
        try:
            normalized_key = self._normalize_key(key)
            async with await self._get_client() as s3:
                response = await s3.get_object(Bucket=bucket_name, Key=normalized_key)
                
                async def stream_content():
                    async with response['Body'] as stream:
                        while True:
                            chunk = await stream.read(8192)  # 8KB chunks
                            if not chunk:
                                break
                            yield chunk
                
                return stream_content()
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(f"Object not found: s3://{bucket_name}/{key}")
                return None
            else:
                logger.error(f"Error streaming object s3://{bucket_name}/{key}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error streaming object: {e}")
            raise

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
        try:
            normalized_key = self._normalize_key(key)
            async with await self._get_client() as s3:
                params = {
                    'Bucket': bucket_name,
                    'Key': normalized_key,
                    'Body': content
                }
                
                if content_type:
                    params['ContentType'] = content_type
                
                if metadata:
                    params['Metadata'] = metadata
                
                await s3.put_object(**params)
                
                return True
                
        except ClientError as e:
            logger.error(f"Error uploading object s3://{bucket_name}/{key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading object: {e}")
            raise

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
        try:
            normalized_key = self._normalize_key(key)
            async with await self._get_client() as s3:
                await s3.delete_object(Bucket=bucket_name, Key=normalized_key)
                
                return True
                
        except ClientError as e:
            logger.error(f"Error deleting object s3://{bucket_name}/{key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting object: {e}")
            raise

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
        try:
            normalized_key = self._normalize_key(key)
            async with await self._get_client() as s3:
                response = await s3.head_object(Bucket=bucket_name, Key=normalized_key)
                
                metadata = {
                    'key': normalized_key,
                    'size': response['ContentLength'],
                    'last_modified': response['LastModified'],
                    'etag': response['ETag'].strip('"'),
                    'content_type': response.get('ContentType', 'binary/octet-stream'),
                    'metadata': response.get('Metadata', {})
                }
                
                return metadata
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.warning(f"Object not found: s3://{bucket_name}/{key}")
                return None
            else:
                logger.error(f"Error getting object metadata s3://{bucket_name}/{key}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error getting object metadata: {e}")
            raise