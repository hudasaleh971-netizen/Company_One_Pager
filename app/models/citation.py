"""
Citation System Models

These Pydantic models support the NotebookLM-style citation system where
source text appears on hover. Uses textual tags [[Src:xxx]] that travel
with content through agent processing.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple
import re
from loguru import logger


def get_page_number(chunk_text: str) -> str:
    """
    Extract page number from chunk text using regex.
    
    Looks for pattern: \n--- PAGE X ---
    
    Args:
        chunk_text: The text chunk from grounding metadata
        
    Returns:
        String like "Page 5" or empty string if not found
    """
    pattern = r"\n--- PAGE (\d+) ---"
    matches = re.findall(pattern, chunk_text)
    
    if matches:
        page_num = f"Page {matches[0]}"
        logger.debug(f"📄 Extracted page number: {page_num}")
        return page_num
    
    logger.debug("⚠️ No page number found in chunk text")
    return ""


# --- OBJECT 1: The Source of Truth ---
# Created during file ingestion. This never changes.
class SourceDocument(BaseModel):
    """
    Represents a single source document/chunk from the annual report.
    This is the source of truth for citations.
    """
    source_id: str = Field(..., description="Unique ID (e.g., 'src_101')")
    title: str = Field(..., description="Filename or Report Title")
    page_number: str = Field(default="", description="Extracted via Regex ('Page 5')")
    raw_text: str = Field(..., description="The original chunk text (for tooltip context)")

    def __repr__(self):
        return f"SourceDocument(id={self.source_id}, page={self.page_number})"


class SourceLibrary(BaseModel):
    """
    A fast lookup dictionary of all source documents.
    """
    sources: Dict[str, SourceDocument] = Field(
        default_factory=dict,
        description="Lookup dict: { 'src_101': SourceDocument, ... }"
    )

    def add_source(self, source: SourceDocument) -> None:
        """Add a source document to the library."""
        self.sources[source.source_id] = source
        logger.debug(f"📚 Added source to library: {source.source_id}")

    def get_source(self, source_id: str) -> Optional[SourceDocument]:
        """Get a source document by ID."""
        return self.sources.get(source_id)



# --- OBJECT 3: The Frontend Payload ---
# What you send to Node.js. Clean text + computed indices.
class CitationMetadata(BaseModel):
    """
    Metadata for a single citation, with calculated indices for the final text.
    """
    start_index: int = Field(..., description="Start of the sentence/phrase in final text")
    end_index: int = Field(..., description="End of the sentence/phrase in final text")
    source_id: str = Field(..., description="Links back to SourceDocument")


class FinalResponse(BaseModel):
    """
    Final payload structure to send to the frontend (Node.js).
    Contains both clean and cited text versions.
    """
    clean_text: str = Field(..., description="Text WITHOUT tags (for reading)")
    cited_text: str = Field(..., description="Text WITH tags (for processing)")
    citations: List[CitationMetadata] = Field(
        default_factory=list,
        description="List of citation metadata with computed indices"
    )
    sources: Dict[str, SourceDocument] = Field(
        default_factory=dict,
        description="Metadata for the tooltips"
    )


def extract_citations_from_tags(text_with_tags: str) -> Tuple[str, List[CitationMetadata]]:
    """
    Parses text with [[Src:x]] tags into clean text and metadata indices.
    Centralized logic used by API and Tests.
    
    Handles both formats:
    - [[Src:101]] - number only
    - [[Src:src_101]] - with src_ prefix
    
    Args:
        text_with_tags: Text with [[Src:xxx]] tags embedded
        
    Returns:
        Tuple of (clean_text, list of CitationMetadata)
    """
    logger.info("🔍 Parsing citation tags from text...")
    
    # Pattern to find [[Src:src_101]] or [[Src:101]]
    tag_pattern = r'\[\[Src:(?:src_)?(\d+)\]\]'
    
    citations = []
    offset = 0
    
    # We use an iterator to find all tags
    matches = list(re.finditer(tag_pattern, text_with_tags))
    
    for match in matches:
        source_num = match.group(1)
        source_id = f"src_{source_num}"
        
        # Calculate where this tag starts in the original tagged string
        original_start = match.start()
        original_end = match.end()
        tag_length = original_end - original_start

        # The location in the "clean" text is: original_position - total_removed_tags_so_far
        current_clean_pos = original_start - offset
        
        # UI NOTE: Currently this creates a "Spot Citation" (start == end).
        # If you want to highlight the sentence, you would need NLP logic here 
        # to look backward from 'current_clean_pos' to find the sentence start.
        citations.append(CitationMetadata(
            start_index=current_clean_pos,
            end_index=current_clean_pos, 
            source_id=source_id
        ))
        
        logger.debug(f"📌 Found citation tag: [[Src:{source_num}]] at clean position {current_clean_pos}")
        offset += tag_length

    # Remove all tags to get the final clean text
    clean_text = re.sub(tag_pattern, '', text_with_tags)
    
    logger.info(f"✅ Parsed {len(citations)} citations from text")
    return clean_text, citations


def create_final_response(
    tagged_text: str, 
    source_library: SourceLibrary
) -> FinalResponse:
    """
    Create a FinalResponse object from tagged text and source library.
    
    Args:
        tagged_text: Text with [[Src:xxx]] tags
        source_library: Library of all source documents
        
    Returns:
        FinalResponse ready to send to frontend
    """
    logger.info("📦 Creating final response payload...")
    
    clean_text, citations = extract_citations_from_tags(tagged_text)
    
    # Filter sources to only those referenced in citations
    referenced_sources = {}
    for citation in citations:
        if citation.source_id in source_library.sources:
            referenced_sources[citation.source_id] = source_library.sources[citation.source_id]
    
    response = FinalResponse(
        clean_text=clean_text,
        cited_text=tagged_text,
        citations=citations,
        sources=referenced_sources
    )
    
    logger.info(f"✅ Final response created with {len(citations)} citations and {len(referenced_sources)} sources")
    return response
