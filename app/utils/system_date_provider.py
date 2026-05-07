"""
Default implementation of date provider using system datetime.
"""
from datetime import datetime, timezone
from app.interfaces.date_provider_interface import IDateProvider


class SystemDateProvider(IDateProvider):
    """Production date provider that uses system datetime."""
    
    def now(self) -> datetime:
        """Get current local datetime."""
        return datetime.now()
    
    def utc_now(self) -> datetime:
        """Get current UTC datetime."""
        return datetime.now(timezone.utc)