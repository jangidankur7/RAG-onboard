"""Document-related models for onboarding service."""
from typing import Optional
from pydantic import Field
from fastapi_camelcase import CamelModel

from .enums import DocumentType


class DocumentInfo(CamelModel):
    """Information about a document associated with an asset."""
    source: str = Field(..., description="Source of the document: 'web' or 'user'")
    status: str = Field(..., description="Processing status: 'pending', 'ingested', or 'failed'")
    s3_key: Optional[str] = Field(None, description="S3 key for the document")
    preview_url: Optional[str] = Field(None, description="URL for document preview")
    file_name: str = Field(..., description="Original filename")
    language: str = Field(default="en", description="Document language")
    page_count: Optional[int] = Field(None, description="Number of pages in document")
    file_size_kb: Optional[int] = Field(None, description="File size in kilobytes")
    confidence: Optional[float] = Field(None, description="Confidence score for web-sourced documents")
    source_url: Optional[str] = Field(None, description="Original URL for web-sourced documents")
    checksum: Optional[str] = Field(None, description="File checksum for integrity verification")
    ingestion_id: Optional[str] = Field(None, description="ID of the ingestion job/process")


class DocumentSearchResult(CamelModel):
    """Result of searching for documents via web search."""
    document_type: DocumentType = Field(..., description="Type of document found")
    url: str = Field(..., description="URL of the document")
    confidence: float = Field(..., description="Confidence score of the match")
    file_name: str = Field(..., description="Suggested filename")
    file_size_kb: Optional[int] = Field(None, description="File size if available")
    preview_url: Optional[str] = Field(None, description="CDN URL for document preview")




