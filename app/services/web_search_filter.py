"""Web search filtering service for document discovery."""
import re
import logging
from typing import List, Dict, Set
from urllib.parse import urlparse

from app.models.document import DocumentSearchResult
from app.models.enums import DocumentType

logger = logging.getLogger(__name__)


class WebSearchFilter:
    """Filters and scores web search results for service manual discovery."""
    
    # INCLUDE keywords for service manual discovery
    INCLUDE_KEYWORDS = [
        'service', 'installation', 'repair', 'support', 'maintenance', 
        'troubleshooting', 'guide', 'manual', 'operat*', 'owner*', 
        'technic*', 'schematic', 'diagram'
    ]
    
    # EXCLUDE keywords for filtering out marketing materials
    EXCLUDE_KEYWORDS = [
        'brochure', 'catalog*', 'sales', 'marketing', 'distribut*'
    ]
    
    # Dynamic list of excluded domains (social media, etc.)
    EXCLUDED_DOMAINS = {
        'twitter.com', 'x.com', 'youtube.com', 'facebook.com', 
        'instagram.com', 'linkedin.com', 'tiktok.com', 'reddit.com',
        'pinterest.com', 'snapchat.com', 'whatsapp.com', 'telegram.org',
        'discord.com', 'slack.com', 'zoom.us', 'teams.microsoft.com'
    }
    
    # High-probability domains that contain OEM information
    OEM_DOMAINS = {
        'manualslib.com', 'manualsonline.com', 'manualslib.com',
        'service-manual.net', 'repair-manual.com', 'owners-manual.com'
    }
    
    def __init__(self):
        """Initialize the web search filter."""
        self._compile_regex_patterns()
    
    def _compile_regex_patterns(self):
        """Compile regex patterns for keyword matching."""
        # Convert wildcard patterns to regex
        include_patterns = []
        for keyword in self.INCLUDE_KEYWORDS:
            if '*' in keyword:
                # Convert wildcard to regex
                pattern = keyword.replace('*', '.*')
                include_patterns.append(f"\\b{pattern}\\b")
            else:
                include_patterns.append(f"\\b{keyword}\\b")
        
        exclude_patterns = []
        for keyword in self.EXCLUDE_KEYWORDS:
            if '*' in keyword:
                pattern = keyword.replace('*', '.*')
                exclude_patterns.append(f"\\b{pattern}\\b")
            else:
                exclude_patterns.append(f"\\b{keyword}\\b")
        
        self.include_regex = re.compile('|'.join(include_patterns), re.IGNORECASE)
        self.exclude_regex = re.compile('|'.join(exclude_patterns), re.IGNORECASE)
    
    def filter_search_results(
        self, 
        doc_type: DocumentType,
        results: List[Dict[str, any]], 
        manufacturer: str, 
        model: str,
        max_results: int = 5
    ) -> List[DocumentSearchResult]:
        """Filter and return multiple high-confidence document search results for the specified document type."""
        filtered_results = []
        
        # Re-rank by the score provided by the search client
        results.sort(key=lambda x: x.get('score', 0.0), reverse=True)
        for result in results:
            try:
                # Extract URL and title
                url = result.get('url', '')
                title = result.get('title', '')
                content = result.get('content', '')
                tavily_score = result.get('score', 0.0)  # Extract Tavily's relevance score
                
                # Combine text for analysis
                combined_text = f"{title} {content}".lower()
                
                # Apply filters
                if not self._is_valid_url(url):
                    continue
                
                if not self._is_pdf_direct_download(url):
                    continue
                
                if self._contains_excluded_keywords(combined_text):
                    continue
                
                if not self._contains_include_keywords(combined_text):
                    continue
                
                # Use Tavily's score directly
                score = tavily_score
                
                # Only include results with score > 0.5
                if score > 0.5:
                    # Use the passed document type instead of determining it
                    # Generate filename
                    filename = self._generate_filename(url, title, manufacturer, model, doc_type)
                    
                    filtered_result = DocumentSearchResult(
                        url=url,
                        document_type=doc_type,
                        confidence=score,
                        file_name=filename
                    )
                    
                    filtered_results.append(filtered_result)
                
            except Exception as e:
                logger.error(f"Error processing search result: {e}")
                continue
        
        # Deduplicate by URL - keep only highest confidence match per URL
        url_best_match = {}
        for result in filtered_results:
            if result.url not in url_best_match or result.confidence > url_best_match[result.url].confidence:
                url_best_match[result.url] = result
        
        # Convert back to list and sort by confidence
        deduplicated_results = list(url_best_match.values())
        deduplicated_results.sort(key=lambda x: x.confidence, reverse=True)
        
        # Return top N results (or all if max_results is None/0)
        return deduplicated_results[:max_results or None]
     
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and not from excluded domains."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www. prefix for comparison
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check against excluded domains
            if domain in self.EXCLUDED_DOMAINS:
                return False
            
            # Check for valid scheme
            if parsed.scheme not in ['http', 'https']:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _is_pdf_direct_download(self, url: str) -> bool:
        """Check if URL is a direct PDF download link."""
        return url.lower().endswith('.pdf')
    
    def _contains_include_keywords(self, text: str) -> bool:
        """Check if text contains any include keywords."""
        return bool(self.include_regex.search(text))
    
    def _contains_excluded_keywords(self, text: str) -> bool:
        """Check if text contains any excluded keywords."""
        return bool(self.exclude_regex.search(text))
    
    def _generate_filename(
        self, 
        url: str, 
        title: str, 
        manufacturer: str, 
        model: str, 
        doc_type: DocumentType
    ) -> str:
        """Generate a clean filename for the document."""
        try:
            # Extract filename from URL
            parsed_url = urlparse(url)
            url_filename = parsed_url.path.split('/')[-1]
            
            # Clean the filename
            if url_filename and url_filename.lower().endswith('.pdf'):
                # Use filename from URL if it looks reasonable
                clean_filename = re.sub(r'[^\w\-_.]', '_', url_filename)
                if len(clean_filename) > 50:  # Truncate if too long
                    clean_filename = clean_filename[:50] + '.pdf'
                return clean_filename
            
        except:
            pass
        
        # Fallback: generate filename from components
        clean_manufacturer = re.sub(r'[^\w\-]', '_', manufacturer)
        clean_model = re.sub(r'[^\w\-]', '_', model)
        doc_type_name = doc_type.value.replace('_', '_')
        
        return f"{clean_manufacturer}_{clean_model}_{doc_type_name}.pdf"
    
    def get_excluded_domains(self) -> Set[str]:
        """Get the current list of excluded domains."""
        return self.EXCLUDED_DOMAINS.copy()
