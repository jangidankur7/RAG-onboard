"""Enums for the onboarding service."""
from enum import Enum


class AssetStatus(str, Enum):
    """Asset onboarding status."""
    SEARCHING = "searching"
    USER_REVIEW = "user_review"
    PROCESSING = "processing"
    INTERNAL_REVIEW = "internal_review"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Supported document types for assets."""
    OPERATOR_GUIDE = "operator_guide"
    SPECIFICATION_SHEET = "specification_sheet"
    SAFETY_GUIDE = "safety_guide"
    CIRCUIT_GUIDE = "circuit_guide"
    MAINTENANCE_GUIDE = "maintenance_guide"
    

class DocumentSource(str, Enum):
    """Source of the document."""
    WEB = "web"
    USER = "user"


class DocumentStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    AVAILABLE = "available"
    INGESTED = "ingested"
    FAILED = "failed"
