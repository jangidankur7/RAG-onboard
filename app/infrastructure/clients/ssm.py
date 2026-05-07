import aioboto3
from typing import Optional
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SSMClient:
    """AWS Systems Manager Parameter Store client."""
    
    REGION = "us-west-2"
    
    def __init__(self):
        """Initialize SSM client."""
        self.region_name = self.REGION
        self._session = None

    async def _get_session(self):
        """Get or create boto3 session."""
        if self._session is None:
            self._session = aioboto3.Session()
        return self._session

    async def get_parameter(self, parameter_name: str, decrypt: bool = True) -> Optional[str]:
        """
        Get parameter value from SSM Parameter Store.
        
        Args:
            parameter_name: Name of the parameter to retrieve
            decrypt: Whether to decrypt secure string parameters
            
        Returns:
            Parameter value or None if not found
        """
        try:
            session = await self._get_session()
            async with session.client('ssm', region_name=self.region_name) as ssm:
                response = await ssm.get_parameter(
                    Name=parameter_name,
                    WithDecryption=decrypt
                )
                return response['Parameter']['Value']
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ParameterNotFound':
                logger.warning(f"SSM parameter not found: {parameter_name}")
                return None
            else:
                logger.error(f"Error retrieving SSM parameter {parameter_name}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving SSM parameter {parameter_name}: {e}")
            raise