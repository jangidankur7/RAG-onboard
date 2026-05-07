"""Asset repository implementation using DynamoDB."""
from typing import Optional, List
from app.interfaces.dynamo_client_interface import IDynamoClient
from app.infrastructure.clients.ddb import FilterCondition, FilterOperator
from app.interfaces.asset_repository_interface import IAssetRepository
from app.models.asset import Asset


class AssetRepository(IAssetRepository):
    """Handles asset data access operations with DynamoDB."""

    table_name = "Assets"

    def __init__(self, dynamo_client: IDynamoClient):
        self._dynamo_client = dynamo_client

    async def get_by_id(self, asset_id: str) -> Optional[Asset]:
        """Get an asset by its ID."""
        try:
            item = await self._dynamo_client.get_item(
                table_name=self.table_name,
                hash_key=asset_id
            )
            
            if not item:
                return None
                
            return Asset(**item)
        
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve asset {asset_id}: {str(e)}")
    
    async def search_by_manufacturer_model(self, manufacturer: str, model: str) -> Optional[Asset]:
        """Search for an asset by manufacturer and model using byMakeModel index."""
        try:
            # TODO: Implement generic GSI query in Dynamo client instead of scan
            # GSI name: byMakeModel
            items = await self._dynamo_client.scan(
                table_name=self.table_name,
                filter_conditions=[
                    FilterCondition(
                        attribute_name="manufacturer",
                        operator=FilterOperator.EQUAL,
                        value=manufacturer.lower().strip()
                    ),
                    FilterCondition(
                        attribute_name="model",
                        operator=FilterOperator.EQUAL,
                        value=model.lower().strip()
                    )
                ]
            )
            
            if not items:
                return None
                
            # Should return at most one result since manufacturer+model should be unique
            return Asset(**items[0])

        except Exception as e:
            raise RuntimeError(f"Failed to search asset by manufacturer {manufacturer} and model {model}: {str(e)}")
      
    async def upsert(self, asset: Asset) -> Asset:
        """Create or update an asset."""
        try:
            asset.manufacturer = asset.manufacturer.lower().strip()
            asset.model = asset.model.lower().strip()
            await self._dynamo_client.upsert(
                table_name=self.table_name,
                item=asset.model_dump()
            )
            
            return asset
            
        except Exception as e:
            raise RuntimeError(f"Failed to upsert asset {asset.asset_id}: {str(e)}")

    async def delete(self, asset_id: str) -> None:
        """Delete an asset by its ID."""
        try:
            await self._dynamo_client.delete(
                table_name=self.table_name,
                key=asset_id
            )            
        except Exception as e:
            raise RuntimeError(f"Failed to delete asset {asset_id}: {str(e)}")
