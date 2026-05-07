"""Interface for web search operations."""
from typing import Protocol, List, Dict, Any, Optional


class IWebSearchClient(Protocol):
    """Interface for web search client."""
    
    async def search(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 10,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Perform a raw web search."""
        ...
    
    async def verify_pdf_url(self, url: str) -> bool:
        """Verify that a URL points to a valid PDF document."""
        ...
    
    async def download_pdf_from_url(self, url: str) -> bytes:
        """Download PDF content from a URL."""
        ...
