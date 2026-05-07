"""Document search service - orchestrates web search, filtering, and document operations."""
import asyncio
import logging
import tempfile
import os
from typing import List, Dict, Any
from datetime import datetime
from injector import inject

from app.interfaces.web_search_interface import IWebSearchClient
from app.interfaces.ragie_client_interface import IRagieClient
from app.interfaces.cdn_repository_interface import ICDNRepository
from app.interfaces.document_search_service_interface import IDocumentSearchService
from app.models.document import DocumentSearchResult, DocumentInfo
from app.models.enums import DocumentSource, DocumentStatus, DocumentType
from app.services.web_search_filter import WebSearchFilter

logger = logging.getLogger(__name__)


class DocumentSearchService(IDocumentSearchService):
    """
    Service layer for document search operations.
    Orchestrates: Web search (Tavily) + Filtering + PDF operations + Vector DB (RAGIE).
    """
    
    @inject
    def __init__(
        self,
        web_search_client: IWebSearchClient,
        ragie_client: IRagieClient,
        cdn_repository: ICDNRepository
    ):
        """Initialize document search service."""
        self.web_search_client = web_search_client
        self.ragie_client = ragie_client
        self.cdn_repository = cdn_repository
        self.filter_service = WebSearchFilter()
    
    async def search_device_documentation(
        self,
        manufacturer: str,
        model: str
    ) -> Dict[DocumentType, DocumentInfo]:
        """
        Search for device documentation using web search with intelligent filtering.
        Verifies, downloads, and uploads valid documents to CDN for user review.
        Returns ready-to-use DocumentInfo objects.
        """
        try:
            # Build search queries - one per DocumentType enum value
            search_queries = {
                DocumentType.OPERATOR_GUIDE: f'"{manufacturer}" "{model}" operator guide user manual PDF filetype:pdf',
                DocumentType.SPECIFICATION_SHEET: f'"{manufacturer}" "{model}" specification sheet datasheet specs PDF filetype:pdf',
                DocumentType.SAFETY_GUIDE: f'"{manufacturer}" "{model}" safety guide safety manual instructions PDF filetype:pdf',
                DocumentType.CIRCUIT_GUIDE: f'"{manufacturer}" "{model}" circuit guide schematic wiring diagram PDF filetype:pdf',
                DocumentType.MAINTENANCE_GUIDE: f'"{manufacturer}" "{model}" maintenance service repair manual PDF filetype:pdf'
            }
            
            # Get excluded domains from filter service
            excluded_domains = list(self.filter_service.get_excluded_domains())
            
            # Create async tasks that include the document type in their result
            async def search_for_doc_type(doc_type: DocumentType, query: str):
                response = await self.web_search_client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=10,
                    exclude_domains=excluded_domains
                )
                return doc_type, response
            
            # Execute all searches concurrently
            search_tasks = [
                search_for_doc_type(doc_type, query)
                for doc_type, query in search_queries.items()
            ]
            
            responses = await asyncio.gather(*search_tasks, return_exceptions=False)
            
            # Organize results by document type
            results_by_type = {}
            for doc_type, response in responses:
                if response and 'results' in response:
                    results_by_type[doc_type] = response['results']
                else:
                    results_by_type[doc_type] = []
            
            # Filter and deduplicate in one pass - pick best unique URL for each document type
            deduplicated_results = self._filter_and_deduplicate_documents(
                results_by_type, manufacturer, model
            )
            
            # Verify, download, and upload valid documents to CDN
            verified_documents = {}
            for doc_type, result in deduplicated_results.items():
                if not result:
                    continue
                doc_info = await self._verify_and_create_document_info(result, manufacturer, model)
                if doc_info:
                    verified_documents[doc_type] = doc_info
            
            return verified_documents
            
        except Exception as e:
            return {}

    def _filter_and_deduplicate_documents(self, results_by_type, manufacturer, model):
        all_candidates_with_types = []
        
        for doc_type, raw_results in results_by_type.items():
            # Reuse existing filtering logic
            filtered_candidates = self.filter_service.filter_search_results(
                doc_type=doc_type,
                results=raw_results,
                manufacturer=manufacturer,
                model=model,
                max_results=5
            )
            
            # Add to global list with document type
            for candidate in filtered_candidates:
                if candidate:
                    all_candidates_with_types.append((candidate, doc_type))
        
        # Sort by confidence and deduplicate across document types
        all_candidates_with_types.sort(key=lambda x: x[0].confidence, reverse=True)
        
        assigned_urls = set()
        document_assignments = {}
        
        # Assign highest confidence candidates first, avoiding duplicate URLs
        for candidate, doc_type in all_candidates_with_types:
            if candidate.url not in assigned_urls and doc_type not in document_assignments:
                document_assignments[doc_type] = candidate
                assigned_urls.add(candidate.url)
        
        # Fill in None for unassigned document types
        for doc_type in results_by_type.keys():
            if doc_type not in document_assignments:
                document_assignments[doc_type] = None
                
        return document_assignments

    async def _verify_and_create_document_info(
        self, 
        result: DocumentSearchResult, 
        manufacturer: str, 
        model: str
    ) -> DocumentInfo:
        """Verify document URL, download content, upload to CDN, and return DocumentInfo."""
        try:
            # Verify URL points to a valid PDF
            is_valid_pdf = await self.web_search_client.verify_pdf_url(result.url)
            
            if not is_valid_pdf:
                return None
            
            # Download the document
            content = await self.web_search_client.download_pdf_from_url(result.url)
            
            if not content:
                return None
            
            # Upload to public CDN for user review
            cdn_path = f"device-docs/{manufacturer}/{model}/{result.document_type.value}/{result.file_name}"
            cdn_url = await self.cdn_repository.upload_file(
                file_path=cdn_path,
                content=content,
                content_type="application/pdf"
            )
            
            # Create and return DocumentInfo
            doc_info = DocumentInfo(
                source=DocumentSource.WEB,
                status=DocumentStatus.PENDING,
                file_name=result.file_name,
                language="en",  # Assume English for web-found documents
                confidence=result.confidence,
                source_url=result.url,
                preview_url=cdn_url,
                file_size_kb=len(content) // 1024
            )
            
            return doc_info
            
        except Exception as e:
            return None

