from typing import Protocol, Optional


class ISSMClient(Protocol):
    """Interface for SSM Parameter Store client."""
    
    async def get_parameter(self, parameter_name: str, decrypt: bool = True) -> Optional[str]:
        """
        Get parameter value from SSM Parameter Store.
        
        Args:
            parameter_name: Name of the parameter to retrieve
            decrypt: Whether to decrypt secure string parameters
            
        Returns:
            Parameter value or None if not found
        """
        ...