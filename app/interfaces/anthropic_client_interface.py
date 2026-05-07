"""Interface for Anthropic client operations."""

from typing import Protocol, List, Dict, Any, Optional


class IAnthropicClient(Protocol):
    """Interface for Anthropic client operations."""
    
    async def generate_response(
        self, 
        prompt: str, 
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Generate a response using Anthropic's API."""
        ...
    
    async def analyze_document(
        self, 
        document_content: str, 
        analysis_type: str = "summary"
    ) -> Dict[str, Any]:
        """Analyze document content using Anthropic."""
        ...
    
    async def extract_information(
        self, 
        text: str, 
        extraction_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract structured information from text."""
        ...
    
    async def search_web_with_tools(
        self, 
        query: str, 
        max_searches: int = 5
    ) -> List[Dict[str, Any]]:
        """Perform web search using Anthropic's web search tools."""
        ...
