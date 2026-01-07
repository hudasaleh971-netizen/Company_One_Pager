"""
Citation System Models

These Pydantic models support the NotebookLM-style citation system where
source text appears on hover. Uses textual tags [[Src:xxx]] that travel
with content through agent processing.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
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


# --- OBJECT 2: The Agent Output ---
# What your Sub-Agents and Consolidation Agent pass around.
class AgentOutput(BaseModel):
    """
    Output structure from sub-agents containing text with embedded citation tags.
    """
    content_with_tags: str = Field(
        ..., 
        description="Text with embedded tags like 'Revenue is up [[Src:101]].'"
    )
    sources: Dict[str, SourceDocument] = Field(
        default_factory=dict,
        description="Source documents referenced by the tags"
    )


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


def parse_tags_to_citations(tagged_text: str) -> tuple[str, List[CitationMetadata]]:
    """
    Parse a tagged text string and extract citation metadata.
    
    Args:
        tagged_text: Text with [[Src:xxx]] tags embedded
        
    Returns:
        Tuple of (clean_text, list of CitationMetadata)
    """
    logger.info("🔍 Parsing citation tags from text...")
    
    # Pattern to find [[Src:xxx]] tags
    tag_pattern = r'\[\[Src:(\w+)\]\]'
    
    citations = []
    clean_text = tagged_text
    offset = 0
    
    for match in re.finditer(tag_pattern, tagged_text):
        source_id = match.group(1)
        tag_start = match.start() - offset
        tag_end = match.end() - offset
        
        # The citation refers to the sentence/phrase BEFORE the tag
        # For simplicity, we'll mark just the tag position for now
        citation = CitationMetadata(
            start_index=tag_start,
            end_index=tag_start,  # Points to where the tag was
            source_id=f"src_{source_id}"
        )
        citations.append(citation)
        logger.debug(f"📌 Found citation tag: [[Src:{source_id}]] at position {tag_start}")
        
        # Remove the tag from clean text
        clean_text = clean_text[:tag_start] + clean_text[tag_end:]
        offset += (tag_end - match.start())
    
    logger.info(f"✅ Parsed {len(citations)} citations from text")
    return clean_text.strip(), citations


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
    
    clean_text, citations = parse_tags_to_citations(tagged_text)
    
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
