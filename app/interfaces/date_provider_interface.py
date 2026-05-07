"""
Interface for date/time providers to enable testable time-dependent code.
"""
from typing import Protocol
from datetime import datetime


class IDateProvider(Protocol):
    """Interface for providing current date/time values."""
    
    def now(self) -> datetime:
        """Get current local datetime."""
        ...
    
    def utcnow(self) -> datetime:
        """Get current UTC datetime."""
        ...