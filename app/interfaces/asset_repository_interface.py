"""Interface for Asset repository operations."""
from typing import Protocol, Optional, List
from app.models.asset import Asset


class IAssetRepository(Protocol):
    """Protocol defining the interface for asset repository operations."""
    
    async def get_by_id(self, asset_id: str) -> Optional[Asset]: ...
    
    async def upsert(self, asset: Asset) -> Asset: ...
    
    async def search_by_manufacturer_model(self, manufacturer: str, model: str) -> Optional[Asset]: ...

    async def delete(self, asset_id: str) -> None: ...