"""Clean Tavily web search client ."""
import logging
import os
from typing import List, Dict, Any, Optional
import httpx
from tavily import AsyncTavilyClient
from injector import inject

from app.interfaces.web_search_interface import IWebSearchClient

logger = logging.getLogger(__name__)


class TavilySearchClient(IWebSearchClient):
    """Clean Tavily web search client ."""
    
    @inject
    def __init__(self):
        """Initialize Tavily search client."""
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY environment variable is required")
        
        self.client = AsyncTavilyClient(api_key=self.api_key)
        self.http_client = httpx.AsyncClient()
        logger.info("Tavily search client initialized")
    
    async def search(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 10,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Perform a raw web search using Tavily."""
        try:
            response = await self.client.search(
                query=query,
                search_depth=search_depth,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                max_results=max_results
            )
            return response
            
        except Exception as e:
            logger.error(f"Tavily search failed for '{query}': {str(e)}")
            return {'results': []}
    
    async def verify_pdf_url(self, url: str) -> bool:
        """Verify that a URL points to a valid PDF document."""
        try:
            # Make a HEAD request to check content type
            response = await self.http_client.head(url, follow_redirects=True, timeout=10.0)
            
            content_type = response.headers.get('content-type', '').lower()
            
            # Check if it's a PDF
            is_pdf = (
                'application/pdf' in content_type or
                url.lower().endswith('.pdf') or
                'pdf' in content_type
            )
            
            return is_pdf
            
        except httpx.TimeoutException:
            logger.warning(f"Timeout verifying PDF URL: {url}")
            # If we timeout, assume it might be a PDF if the URL ends with .pdf
            return url.lower().endswith('.pdf')
        except Exception as e:
            logger.warning(f"Error verifying PDF URL {url}: {str(e)}")
            # Fallback to URL-based detection
            return url.lower().endswith('.pdf')
    
    async def download_pdf_from_url(self, url: str) -> bytes:
        """Download PDF content from a URL."""
        try:
            response = await self.http_client.get(
                url,
                follow_redirects=True,
                timeout=60.0,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; DocumentBot/1.0)'}
            )
            response.raise_for_status()
            
            content = response.content
            
            # Verify it's actually a PDF
            if not content.startswith(b'%PDF-'):
                raise ValueError(f"Downloaded content from {url} is not a valid PDF")
            
            return content
            
        except httpx.TimeoutException as e:
            logger.error(f"Timeout downloading PDF from {url}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading PDF from {url}: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Failed to download PDF from {url}: {str(e)}")
            raise

