"""Pydantic models for RAGIE API integration."""

from typing import Optional, List, Dict, Any
from pydantic import Field
from fastapi_camelcase import CamelModel
from datetime import datetime


class RAGIEUploadRequest(CamelModel):
    """Request model for uploading a PDF to RAGIE."""
    filename: str = Field(..., description="Name of the PDF file")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata for the document")


class RAGIEUploadResponse(CamelModel):
    """Response model for PDF upload to RAGIE."""
    success: bool = Field(..., description="Whether the upload was successful")
    message: str = Field(..., description="Status message")
    document_id: Optional[str] = Field(None, description="ID of the uploaded document")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional upload details")


class RAGIEDeviceSearchRequest(CamelModel):
    """Request model for finding device PDFs."""
    make: str = Field(..., description="Device manufacturer")
    model: str = Field(..., description="Device model")
    max_uploads: Optional[int] = Field(5, description="Maximum number of documents to upload (default: 5)")


class RAGIEDocumentInfo(CamelModel):
    """Information about a RAGIE document."""
    id: str = Field(..., description="Document ID")
    name: str = Field(..., description="Document name")
    document_type: Optional[str] = Field(None, description="Type of document")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Document metadata")


class RAGIESuccessfulUpload(CamelModel):
    """Information about a successful PDF upload."""
    url: str = Field(..., description="Source URL of the PDF")
    filename: str = Field(..., description="Name of the uploaded file")
    result: Dict[str, Any] = Field(..., description="Upload result details")
    score: Optional[float] = Field(None, description="Relevance score from search (0-1)")
    title: Optional[str] = Field(None, description="Document title")
    source: Optional[str] = Field(None, description="Source domain")
    document_type: Optional[str] = Field(None, description="Type of document")


class RAGIEFailedDownload(CamelModel):
    """Information about a failed PDF download."""
    url: str = Field(..., description="URL that failed to download")
    error: str = Field(..., description="Error message")
    score: Optional[float] = Field(None, description="Relevance score from search (0-1)")


class RAGIEDeviceSearchResponse(CamelModel):
    """Response model for device PDF search and upload."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")
    total_found: Optional[int] = Field(None, description="Total number of PDFs found")
    total_uploaded: Optional[int] = Field(None, description="Total number of PDFs uploaded")
    successful_uploads: Optional[List[RAGIESuccessfulUpload]] = Field(None, description="Successfully uploaded PDFs")
    failed_downloads: Optional[List[RAGIEFailedDownload]] = Field(None, description="Failed downloads")
    suggestions: Optional[List[str]] = Field(None, description="Suggestions if no PDFs found")
    details: Optional[str] = Field(None, description="Additional details")


class RAGIEDeleteRequest(CamelModel):
    """Request model for deleting a document from RAGIE."""
    document_id: str = Field(..., description="ID of the document to delete")


class RAGIEDeleteResponse(CamelModel):
    """Response model for document deletion from RAGIE."""
    success: bool = Field(..., description="Whether the deletion was successful")
    message: str = Field(..., description="Status message")
    document_id: str = Field(..., description="ID of the deleted document")


class RAGIEListResponse(CamelModel):
    """Response model for listing documents from RAGIE."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")
    documents: List[RAGIEDocumentInfo] = Field(..., description="List of documents")
    total_count: int = Field(..., description="Total number of documents")


class RAGIEHealthResponse(CamelModel):
    """Response model for RAGIE service health check."""
    service_available: bool = Field(..., description="Whether RAGIE service is available")
    api_key_configured: bool = Field(..., description="Whether API key is configured")
    anthropic_key_configured: bool = Field(..., description="Whether Anthropic API key is configured")
    message: str = Field(..., description="Health status message")
