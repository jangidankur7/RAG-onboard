"""Utility functions for checksum calculation."""
import hashlib


def calculate_checksum(content: bytes) -> str:
    """Calculate SHA-256 checksum of document content.
    
    Args:
        content: The bytes content to calculate checksum for
        
    Returns:
        SHA-256 hexadecimal digest string
    """
    return hashlib.sha256(content).hexdigest()
