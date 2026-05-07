"""Anthropic API client implementation."""
import os
from injector import inject

from app.interfaces.anthropic_client_interface import IAnthropicClient


class AnthropicClient(IAnthropicClient):
    """Anthropic API client implementation."""
    
    @inject
    def __init__(self):
        """Initialize Anthropic client."""
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
