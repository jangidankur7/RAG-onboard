import aioboto3
from typing import Dict, List, Optional, Any, TypeVar
from decimal import Decimal
from dataclasses import dataclass, asdict, is_dataclass
from enum import Enum
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from datetime import datetime
from app.interfaces.memory_cache_interface import IMemoryCache

T = TypeVar('T')

class FilterOperator(Enum):
    """DynamoDB filter operators"""
    EQUAL = "="
    NOT_EQUAL = "<>"
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    BEGINS_WITH = "begins_with"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    BETWEEN = "between"
    IN = "in"
    EXISTS = "attribute_exists"
    NOT_EXISTS = "attribute_not_exists"

@dataclass
class FilterCondition:
    """Represents a DynamoDB filter condition."""
    attribute_name: str
    operator: FilterOperator
    value: Any
    value2: Optional[Any] = None

@dataclass
class TableKeyNames:
    """Cached table key schema information."""
    partition_key: str
    sort_key: Optional[str] = None

class DynamoClient:
    """DynamoDB client with schema caching and type conversion."""
    
    TABLE_NAME_PREFIX = "chat.onboarding."
    REGION = "us-west-2"
    
    def __init__(self, memory_cache: IMemoryCache):
        """
        Initialize DynamoDB client with injected memory cache.
        
        Args:
            memory_cache: Injected memory cache for table schema caching
        """
        self._cache = memory_cache
        self.region_name = self.REGION
        self._session = None

    async def _get_session(self):
        """Gets or creates aioboto3 session using default credential chain."""
        if self._session is None:
            try:
                # aioboto3 automatically uses the AWS credential chain:
                # 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
                # 2. IAM roles for EC2/ECS/Lambda
                # 3. AWS credentials file
                # 4. Instance profiles, etc.
                self._session = aioboto3.Session(region_name=self.region_name)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize aioboto3 session: {str(e)}")
        return self._session

    async def _get_client(self):
        """Get DynamoDB client."""
        session = await self._get_session()
        return session.client('dynamodb', region_name=self.region_name)

    async def _get_resource(self):
        """Get DynamoDB resource."""
        session = await self._get_session()
        return session.resource('dynamodb', region_name=self.region_name)

    def _log_operation(self, operation: str, table_name: str, **kwargs):
        """Log DynamoDB operations to console"""
        full_table_name = self._get_full_table_name(table_name)
        log_message = f"DDB Operation: {operation} | Table: {full_table_name}"
        
        # Add additional context if provided
        if kwargs:
            context_parts = []
            for key, value in kwargs.items():
                if value is not None:
                    context_parts.append(f"{key}={value}")
            if context_parts:
                log_message += f" | {', '.join(context_parts)}"
        
        print(log_message)  # Console logging

    async def scan(self, table_name: str, filter_conditions: List[FilterCondition] = None) -> List[T]:
        """
        Scan table with optional filtering and automatic pagination.
        
        Args:
            table_name: DynamoDB table name (without prefix)
            filter_conditions: Optional list of filter conditions
            
        Returns:
            List of items matching the filter criteria
        """
        if not table_name:
            raise ValueError("Table name cannot be null or empty")
            
        try:
            full_table_name = self._get_full_table_name(table_name)
            
            async with (await self._get_resource()) as resource:
                table = await resource.Table(full_table_name)
                
                scan_kwargs = {}
                
                if filter_conditions:
                    filter_expression, attr_values, attr_names = self._build_filter_expression(filter_conditions)
                    if filter_expression:
                        scan_kwargs.update({
                            'FilterExpression': filter_expression,
                            'ExpressionAttributeValues': attr_values,
                            'ExpressionAttributeNames': attr_names
                        })
                
                results = []
                response = await table.scan(**scan_kwargs)
                results.extend(response.get('Items', []))
                
                while 'LastEvaluatedKey' in response:
                    scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                    response = await table.scan(**scan_kwargs)
                    results.extend(response.get('Items', []))
                
                return [self._convert_to_python_types(item) for item in results]
                
        except ClientError as e:
            raise RuntimeError(f"Failed to scan table '{table_name}': {e.response['Error']['Message']}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during scan: {str(e)}")

    async def get_item(self, table_name: str, hash_key: str, sort_key: str = None) -> Optional[T]:
        """
        Get single item by primary key.
        
        Args:
            table_name: DynamoDB table name (without prefix)
            hash_key: Partition key value (for composite-key tables)
            sort_key: Sort key value (for composite-key tables)

        Returns:
            Item if found, None otherwise
        """
        if not table_name:
            raise ValueError("Table name cannot be null or empty")
            
        if not hash_key:
            raise ValueError("Either 'key' or both 'hash_key' and 'sort_key' must be provided")
        elif sort_key:
            return await self._get_item_with_composite_key(table_name, hash_key, sort_key)
        else:
            return await self._get_item_with_single_key(table_name, hash_key)

    async def get_items(self, table_name: str, hash_key: str, 
                  sort_key_from: str = None, sort_key_to: str = None,
                  filter_conditions: List[FilterCondition] = None,
                  limit: int | None = None,
                  scan_forward: bool = True) -> List[T]:
        """
        Get multiple items by partition key with optional sort key range and filtering.
        
        Args:
            table_name: DynamoDB table name (without prefix)
            hash_key: Partition key value to query
            sort_key_from: Start of sort key range (optional)
            sort_key_to: End of sort key range (optional)
            filter_conditions: Optional list of filter conditions
            
        Returns:
            List of items matching the query criteria
        """
        if not table_name:
            raise ValueError("Table name cannot be null or empty")
        if not hash_key:
            raise ValueError("Hash key cannot be null or empty")
            
        # Build base query kwargs
        if sort_key_from and sort_key_to:
            query_kwargs = await self._build_sort_range_query(table_name, hash_key, sort_key_from, sort_key_to)
        else:
            query_kwargs = await self._build_partition_key_query(table_name, hash_key)
        
        # Add filter expression if provided
        if filter_conditions:
            self._add_filter_to_query(query_kwargs, filter_conditions)
        
        query_kwargs['ScanIndexForward'] = scan_forward

        return await self._query_items_internal(table_name, query_kwargs, total_limit=limit)
        
    async def get_last_item(self, table_name: str, hash_key: str) -> Optional[T]:
        """
        Get the last item in a specific table by partition key.
        """
        if not table_name:
            raise ValueError("Table name cannot be null or empty")
        if not hash_key:
            raise ValueError("Hash key cannot be null or empty")

        try:
            key_names = await self._get_table_key_names(table_name)
            full_table_name = self._get_full_table_name(table_name)
            
            async with (await self._get_resource()) as resource:
                table = await resource.Table(full_table_name)
                response = await table.query(
                    KeyConditionExpression=Key(key_names.partition_key).eq(hash_key),
                    ScanIndexForward=False,  # Sort descending to fetch the latest item
                    Limit=1,
                )
                items = response.get("Items", [])
                if items:
                    return self._convert_to_python_types(items[0])
                return None
        except ClientError as e:
            raise RuntimeError(f"Failed to get last item from table '{table_name}': {e.response['Error']['Message']}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during get last item: {str(e)}")

    async def upsert(self, table_name: str, item: T) -> None:
        """
        Insert or update an item in the table.
        
        Args:
            table_name: DynamoDB table name (without prefix)
            item: Item to insert or update
        """
        if not table_name:
            raise ValueError("Table name cannot be null or empty")
        if item is None:
            raise ValueError("Item cannot be null")
            
        try:
            full_table_name = self._get_full_table_name(table_name)
            
            async with (await self._get_resource()) as resource:
                table = await resource.Table(full_table_name)
                item_converted = self._convert_to_dynamodb_types(item)
                await table.put_item(Item=item_converted)
            
        except ClientError as e:
            raise RuntimeError(f"Failed to upsert item in table '{table_name}': {e.response['Error']['Message']}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during upsert: {str(e)}")

    async def delete(self, table_name: str, key: str = None, 
               range_key: str = None, sort_key: str = None) -> None:
        """
        Delete an item from the table.
        
        Args:
            table_name: DynamoDB table name (without prefix)
            key: Partition key value (for single-key tables)
            range_key: Partition key value (for composite-key tables)
            sort_key: Sort key value (for composite-key tables)
        """
        if not table_name:
            raise ValueError("Table name cannot be null or empty")
            
        if range_key and sort_key:
            await self._delete_item_with_composite_key(table_name, range_key, sort_key)
        elif key:
            await self._delete_item_with_single_key(table_name, key)
        else:
            raise ValueError("Either 'key' or both 'range_key' and 'sort_key' must be provided")

    async def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists.
        
        Args:
            table_name: DynamoDB table name (without prefix)
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            full_table_name = self._get_full_table_name(table_name)
            
            async with (await self._get_resource()) as resource:
                table = await resource.Table(full_table_name)
                await table.load()
                return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            raise
        except Exception:
            return False

    def _get_full_table_name(self, table_name: str) -> str:
        """Apply table name prefix"""
        return f"{self.TABLE_NAME_PREFIX}{table_name}"

    def _convert_to_python_types(self, obj: Any) -> Any:
        """Convert DynamoDB Decimal objects to Python native types"""
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_to_python_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_python_types(v) for v in obj]
        return obj

    def _convert_to_dynamodb_types(self, obj: Any) -> Any:
        """Convert Python types to DynamoDB-compatible types"""
        if isinstance(obj, datetime):
            # Convert datetime to ISO string
            return obj.isoformat()
        elif is_dataclass(obj):
            # Convert dataclass to dictionary, then recursively convert
            obj_dict = asdict(obj)
            return self._convert_to_dynamodb_types(obj_dict)
        elif isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._convert_to_dynamodb_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_dynamodb_types(v) for v in obj]
        return obj

    async def _get_table_key_names(self, table_name: str) -> TableKeyNames:
        """Get table key schema with memory cache"""
        cache_key = f"ddb.tableKeys.{table_name}"
        
        # Try to get from cache first
        cached_schema = self._cache.get(cache_key)
        if cached_schema is not None:
            return cached_schema

        try:
            full_table_name = self._get_full_table_name(table_name)
            
            async with (await self._get_client()) as client:
                response = await client.describe_table(TableName=full_table_name)
            
            key_schema = response['Table']['KeySchema']
            partition_key = next(k['AttributeName'] for k in key_schema if k['KeyType'] == 'HASH')
            sort_key = next((k['AttributeName'] for k in key_schema if k['KeyType'] == 'RANGE'), None)
            
            key_names = TableKeyNames(partition_key=partition_key, sort_key=sort_key)        
            
            # Cache the result with 12-hour TTL (table schemas rarely change)
            self._cache.set(cache_key, key_names, ttl_seconds=12 * 3600)
            
            return key_names
            
        except ClientError as e:
            raise RuntimeError(f"Failed to describe table '{table_name}': {e.response['Error']['Message']}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error describing table '{table_name}': {str(e)}")

    def _build_filter_expression(self, filter_conditions: List[FilterCondition]) -> tuple:
        """Build DynamoDB filter expression from conditions"""
        if not filter_conditions:
            return None, {}, {}
        
        filter_expressions = []
        expression_attribute_values = {}
        expression_attribute_names = {}
        
        for i, condition in enumerate(filter_conditions):
            if not condition.attribute_name:
                continue
                
            attr_name_token = f"#attr{i}"
            value_token = f":val{i}"
            
            expression_attribute_names[attr_name_token] = condition.attribute_name
            expression_attribute_values[value_token] = condition.value
            
            if condition.operator == FilterOperator.EQUAL:
                filter_expressions.append(f"{attr_name_token} = {value_token}")
            elif condition.operator == FilterOperator.NOT_EQUAL:
                filter_expressions.append(f"{attr_name_token} <> {value_token}")
            elif condition.operator == FilterOperator.LESS_THAN:
                filter_expressions.append(f"{attr_name_token} < {value_token}")
            elif condition.operator == FilterOperator.LESS_THAN_OR_EQUAL:
                filter_expressions.append(f"{attr_name_token} <= {value_token}")
            elif condition.operator == FilterOperator.GREATER_THAN:
                filter_expressions.append(f"{attr_name_token} > {value_token}")
            elif condition.operator == FilterOperator.GREATER_THAN_OR_EQUAL:
                filter_expressions.append(f"{attr_name_token} >= {value_token}")
            elif condition.operator == FilterOperator.BEGINS_WITH:
                filter_expressions.append(f"begins_with({attr_name_token}, {value_token})")
            elif condition.operator == FilterOperator.CONTAINS:
                filter_expressions.append(f"contains({attr_name_token}, {value_token})")
            elif condition.operator == FilterOperator.NOT_CONTAINS:
                filter_expressions.append(f"NOT contains({attr_name_token}, {value_token})")
            elif condition.operator == FilterOperator.BETWEEN:
                value2_token = f":val{i}_2"
                expression_attribute_values[value2_token] = condition.value2
                filter_expressions.append(f"{attr_name_token} BETWEEN {value_token} AND {value2_token}")
            elif condition.operator == FilterOperator.EXISTS:
                filter_expressions.append(f"attribute_exists({attr_name_token})")
                del expression_attribute_values[value_token]
            elif condition.operator == FilterOperator.NOT_EXISTS:
                filter_expressions.append(f"attribute_not_exists({attr_name_token})")
                del expression_attribute_values[value_token]
        
        if not filter_expressions:
            return None, {}, {}
            
        filter_expression = " AND ".join(filter_expressions)
        return filter_expression, expression_attribute_values, expression_attribute_names

    async def _get_item_with_single_key(self, table_name: str, key: str) -> Optional[T]:
        """Get item with single partition key"""
        if not key:
            raise ValueError("Key cannot be null or empty")
            
        key_names = await self._get_table_key_names(table_name)
        key_dict = {key_names.partition_key: key}
        
        return await self._get_item_internal(table_name, key_dict)

    async def _get_item_with_composite_key(self, table_name: str, range_key: str, sort_key: str) -> Optional[T]:
        """Get item with composite key"""
        if not range_key:
            raise ValueError("Range key cannot be null or empty")
        if not sort_key:
            raise ValueError("Sort key cannot be null or empty")
            
        key_names = await self._get_table_key_names(table_name)
        key_dict = {
            key_names.partition_key: range_key,
            key_names.sort_key: sort_key
        }
        
        return await self._get_item_internal(table_name, key_dict)

    async def _get_item_internal(self, table_name: str, key_dict: Dict[str, str]) -> Optional[T]:
        """Internal method to get item by key dictionary"""
        try:
            full_table_name = self._get_full_table_name(table_name)
            
            async with (await self._get_resource()) as resource:
                table = await resource.Table(full_table_name)
                response = await table.get_item(Key=key_dict)
                
                if 'Item' not in response:
                    return None
                    
                return self._convert_to_python_types(response['Item'])
            
        except ClientError as e:
            raise RuntimeError(f"Failed to get item from table '{table_name}': {e.response['Error']['Message']}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during get_item: {str(e)}")

    async def _build_partition_key_query(self, table_name: str, range_key: str) -> dict:
        """Build query kwargs for partition key only"""
        key_names = await self._get_table_key_names(table_name)
        return {
            'KeyConditionExpression': Key(key_names.partition_key).eq(range_key)
        }

    async def _build_sort_range_query(self, table_name: str, range_key: str, 
                               sort_key_from: str, sort_key_to: str) -> dict:
        """Build query kwargs for partition key and sort key range"""
        if not sort_key_from:
            raise ValueError("Sort key FROM cannot be null or empty")
        if not sort_key_to:
            raise ValueError("Sort key TO cannot be null or empty")
            
        key_names = await self._get_table_key_names(table_name)
        return {
            'KeyConditionExpression': (
                Key(key_names.partition_key).eq(range_key) & 
                Key(key_names.sort_key).between(sort_key_from, sort_key_to)
            )
        }

    def _add_filter_to_query(self, query_kwargs: dict, filter_conditions: List[FilterCondition]) -> None:
        """Add filter expression to existing query kwargs"""
        filter_expression, attr_values, attr_names = self._build_filter_expression(filter_conditions)
        if filter_expression:
            query_kwargs['FilterExpression'] = filter_expression
            query_kwargs['ExpressionAttributeValues'] = attr_values
            query_kwargs['ExpressionAttributeNames'] = attr_names

    async def _query_items_internal(self, table_name: str, query_kwargs: dict, total_limit: int | None = None) -> List[T]:
        """Internal method to execute query with pagination"""
        try:
            full_table_name = self._get_full_table_name(table_name)
            
            async with (await self._get_resource()) as resource:
                table = await resource.Table(full_table_name)
                
                results = []
                fetched = 0
                while True:
                    if total_limit is not None:
                        remaining = total_limit - fetched
                        if remaining <= 0:
                            break
                        query_kwargs['Limit'] = remaining

                    response = await table.query(**query_kwargs)
                    items = response.get('Items', [])
                    results.extend(items)
                    fetched += len(items)

                    lek = response.get('LastEvaluatedKey')
                    if not lek:
                        break
                    if total_limit is not None and fetched >= total_limit:
                        break
                    query_kwargs['ExclusiveStartKey'] = lek
                
                return [self._convert_to_python_types(item) for item in results]
            
        except ClientError as e:
            raise RuntimeError(f"Failed to query table '{table_name}': {e.response['Error']['Message']}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during query: {str(e)}")

    async def _delete_item_with_single_key(self, table_name: str, key: str) -> None:
        """Delete item with single partition key"""
        if not key:
            raise ValueError("Key cannot be null or empty")
            
        key_names = await self._get_table_key_names(table_name)
        key_dict = {key_names.partition_key: key}
        
        await self._delete_item_internal(table_name, key_dict)

    async def _delete_item_with_composite_key(self, table_name: str, range_key: str, sort_key: str) -> None:
        """Delete item with composite key"""
        if not range_key:
            raise ValueError("Range key cannot be null or empty")
        if not sort_key:
            raise ValueError("Sort key cannot be null or empty")
            
        key_names = await self._get_table_key_names(table_name)
        key_dict = {
            key_names.partition_key: range_key,
            key_names.sort_key: sort_key
        }
        
        await self._delete_item_internal(table_name, key_dict)

    async def _delete_item_internal(self, table_name: str, key_dict: Dict[str, str]) -> None:
        """Internal method to delete item by key dictionary"""
        try:
            full_table_name = self._get_full_table_name(table_name)
            
            async with (await self._get_resource()) as resource:
                table = await resource.Table(full_table_name)
                await table.delete_item(Key=key_dict)
            
        except ClientError as e:
            raise RuntimeError(f"Failed to delete item from table '{table_name}': {e.response['Error']['Message']}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during delete_item: {str(e)}")

    