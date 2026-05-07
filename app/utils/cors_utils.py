"""CORS utilities for managing allowed origins."""
import os
from typing import List


def get_allowed_origins() -> List[str]:
    """
    Get the list of allowed CORS origins.
    
    Combines hardcoded origins with environment variable CORS_ALLOWED_ORIGINS.
    Ensures no duplicates and returns a clean list of origins.
    
    Returns:
        List of allowed CORS origins
    """
    # Hardcoded origins that are always allowed
    hardcoded_origins = [
        "http://localhost:3000",
        "https://localhost:3000",
        "https://chat.arkim.ai",
        "https://chat-test.arkim.ai"
    ]
    
    # Start with hardcoded origins and track what we've seen
    unique_origins = hardcoded_origins.copy()
    seen = set(hardcoded_origins)
    
    # Get additional origins from environment variable
    cors_env_var = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
    
    if cors_env_var:
        # Split by semicolon and add unique origins
        for origin in cors_env_var.split(";"):
            origin = origin.strip()
            if origin and origin not in seen:
                unique_origins.append(origin)
                seen.add(origin)
    
    return unique_origins