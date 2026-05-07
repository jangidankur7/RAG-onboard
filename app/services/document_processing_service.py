"""Document processing service for OCR and ingestion."""
import logging
import hashlib
import asyncio
from typing import Optional
from datetime import datetime
from injector import inject
import io

from app.interfaces.asset_repository_interface import IAssetRepository
from app.interfaces.private_documents_repository_interface import IPrivateDocumentsRepository
from app.interfaces.cdn_repository_interface import ICDNRepository
from app.interfaces.date_provider_interface import IDateProvider
from app.interfaces.document_processing_service_interface import IDocumentProcessingService
from app.infrastructure.clients.ragie import RagieClient
from app.utils.checksum import calculate_checksum
from app.models.asset import Asset
from app.models.document import DocumentInfo
from app.models.enums import AssetStatus, DocumentStatus, DocumentSource

logger = logging.getLogger(__name__)


class DocumentProcessingService(IDocumentProcessingService):
    """Service for processing documents through OCR and ingestion."""
    
    @inject
    def __init__(
        self,
        asset_repository: IAssetRepository,
        document_storage: IPrivateDocumentsRepository,
        cdn_repository: ICDNRepository,
        ragie_client: RagieClient,
        date_provider: IDateProvider
    ):
        """Initialize document processing service."""
        self.asset_repository = asset_repository
        self.document_storage = document_storage
        self.date_provider = date_provider
        self.cdn_repository = cdn_repository
        self.ragie_client = ragie_client

    async def process_asset_document(self, asset: Asset, document_type: str) -> None:
        """Process a single document: move to private S3 (if needed), generate metadata, and ingest to RAGIE."""
        if document_type not in asset.documents:
                return
            
        doc_info = asset.documents[document_type]
        
        # Handle user documents vs auto-sourced documents differently
        if doc_info.source == DocumentSource.USER:
            # User documents are already in private S3, just get the content
            if not doc_info.s3_key:
                raise ValueError(f"No S3 key found for user document {document_type}")
            
            # Extract S3 key from full URI (s3://bucket/key -> key)
            s3_key = doc_info.s3_key
            if s3_key.startswith('s3://'):
                # Extract just the key part after bucket name
                parts = s3_key.replace('s3://', '').split('/', 1)
                if len(parts) > 1:
                    s3_key = parts[1]  # Everything after bucket name
            
            content = await self.document_storage.get_document(s3_key)
            if not content:
                raise ValueError(f"Failed to retrieve user document from S3: {s3_key}")
                
            # S3 location is already set, just update file size if needed
            if not doc_info.file_size_kb:
                doc_info.file_size_kb = len(content) // 1024
        else:
            # Auto-sourced documents: download from public CDN and move to private S3
            if not doc_info.preview_url:
                raise ValueError(f"No preview URL found for document {document_type}")
            
            # CDN repository handles URL parsing internally
            content = await self.cdn_repository.get_file_content(doc_info.preview_url)
            if not content:
                raise ValueError(f"Failed to download document content from CDN: {doc_info.preview_url}")
            
            # Move document to private S3 storage
            private_s3_key = f"assets/{asset.asset_id}/documents/{document_type}/{doc_info.file_name}"
            s3_uri = await self.document_storage.upload_document(
                private_s3_key, 
                content, 
                content_type="application/pdf"
            )
            await self.cdn_repository.delete_file(doc_info.preview_url)
            
            # Update document info with S3 location
            doc_info.s3_key = s3_uri
            doc_info.file_size_kb = len(content) // 1024
        
        # Now process the document (checksum, page count, preview, RAGIE ingestion)
        await self._process_single_document(doc_info, content, asset, document_type)
        
        # Mark as ingested
        doc_info.status = DocumentStatus.INGESTED

    async def _process_single_document(self, doc_info: DocumentInfo, content, asset: Asset, doc_type: str) -> None:
        """Process a single document through OCR and ingestion."""
        # Extract document metadata
        page_count = await self._get_pdf_page_count(content)
        checksum = calculate_checksum(content)
        
        # Update document info with metadata
        doc_info.page_count = page_count
        doc_info.checksum = checksum

        # Upload to RAGIE with metadata
        doc_info.ingestion_id = await self.ragie_client.upload_document_content(
            content, doc_info.file_name, asset.asset_id, doc_type, asset.manufacturer, asset.model
        )
        
        # Generate preview from first 2 pages
        preview_content = await self._generate_pdf_preview(content)
        
        # Upload preview to CDN
        preview_key = f"previews/{asset.asset_id}/{doc_type}.pdf"
        preview_url = await self.cdn_repository.upload_file(
            preview_key, preview_content, content_type="application/pdf"
        )
        doc_info.preview_url = preview_url


    async def _get_pdf_page_count(self, content: bytes) -> int:
        """Get the number of pages in a PDF using PyMuPDF."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=content, filetype="pdf")
            page_count = len(doc)
            doc.close()
            return page_count
        except ImportError:
            raise RuntimeError("PyMuPDF (fitz) is required for PDF processing. Install with: pip install PyMuPDF")
        except Exception as e:
            logger.warning(f"Failed to get PDF page count: {str(e)}")
            return 0
    
    async def _generate_pdf_preview(self, content: bytes) -> bytes:
        """Generate a preview PDF with the first 2 pages from the original PDF."""
        # Run CPU-intensive PDF processing in thread pool to avoid blocking event loop
        return await asyncio.to_thread(self._generate_pdf_preview_sync, content)
    
    def _generate_pdf_preview_sync(self, content: bytes) -> bytes:
        """Synchronous PDF preview generation with first 2 pages using PyMuPDF (runs in thread pool)."""
        try:
            import fitz  # PyMuPDF - required dependency
        except ImportError:
            raise RuntimeError("PyMuPDF (fitz) is required for PDF preview generation. Install with: pip install PyMuPDF")
        
        try:
            # Open source PDF
            source_pdf = fitz.open(stream=content, filetype="pdf")
            
            if len(source_pdf) == 0:
                source_pdf.close()
                raise ValueError("Source PDF contains no pages")
            
            # Create new PDF for preview
            preview_pdf = fitz.open()  # Empty PDF
            
            # Copy first 2 pages (or fewer if document has less)
            pages_to_copy = min(2, len(source_pdf))
            
            for page_num in range(pages_to_copy):
                # Insert page from source to preview
                preview_pdf.insert_pdf(source_pdf, from_page=page_num, to_page=page_num)
            
            # Ensure we have pages before trying to save
            if len(preview_pdf) == 0:
                source_pdf.close()
                preview_pdf.close()
                raise ValueError("Failed to copy pages to preview PDF")
            
            # Get PDF bytes
            preview_bytes = preview_pdf.tobytes()
            
            # Close documents
            source_pdf.close()
            preview_pdf.close()
            
            return preview_bytes
            
        except Exception as e:
            logger.error(f"PyMuPDF preview generation failed: {str(e)}")
            raise RuntimeError(f"PDF preview generation failed: {str(e)}")
