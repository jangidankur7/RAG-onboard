"""
DynamoDB client interface for dependency injection.
"""
from typing import Protocol, List, Optional, Any, TypeVar, Dict
from app.infrastructure.clients.ddb import FilterCondition

T = TypeVar('T')


class IDynamoClient(Protocol):
    """Protocol defining the interface for DynamoDB client operations."""
    
    async def get_items(
        self, 
        table_name: str, 
        hash_key: str, 
        sort_key: Optional[str] = None
    ) -> List[dict]:
        """
        Get items from DynamoDB table by key.
        
        Args:
            table_name: Name of the table
            hash_key: Partition key value
            sort_key: Sort key value (optional)
            
        Returns:
            List of items matching the key
        """
        ...
    
    async def get_item(
        self, 
        table_name: str, 
        hash_key: str, 
        sort_key: Optional[str] = None
    ) -> Optional[T]:
        """
        Get a single item from DynamoDB table by key.
        
        Args:
            table_name: Name of the table
            hash_key: Partition key value
            sort_key: Sort key value (optional)
            
        Returns:
            Item matching the key or None
        """
        ...
    
    async def scan(
        self, 
        table_name: str, 
        filter_conditions: Optional[List[FilterCondition]] = None
    ) -> List[T]:
        """
        Scan table with optional filtering.
        
        Args:
            table_name: Name of the table
            filter_conditions: Optional filter conditions
            
        Returns:
            List of items matching the filter criteria
        """
        ...
    
    async def upsert(self, table_name: str, item: T) -> None:
        """
        Insert or update an item in DynamoDB table.
        
        Args:
            table_name: Name of the table
            item: Item to insert or update
        """
        ...
    
    async def delete(
        self, 
        table_name: str, 
        key: Optional[str] = None,
        range_key: Optional[str] = None,
        sort_key: Optional[str] = None
    ) -> None:
        """
        Delete an item from DynamoDB table.
        
        Args:
            table_name: Name of the table
            key: Key for single-key tables
            range_key: Partition key for composite-key tables
            sort_key: Sort key for composite-key tables
        """
        ...
    
    async def get_last_item(self, table_name: str, hash_key: str) -> Optional[T]:
        """
        Get the last item for a given hash key.
        
        Args:
            table_name: Name of the table
            hash_key: Partition key value
            
        Returns:
            Last item or None
        """
        ...
    
    async def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists.
        
        Args:
            table_name: Name of the table
            
        Returns:
            True if table exists
        """
        ...
