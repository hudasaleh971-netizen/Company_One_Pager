import time
import textwrap
import re
from typing import Dict, Any, Optional
from google.genai import types, client
from loguru import logger
from app.config import GEMINI_API_KEY, GEMINI_MODEL_NAME
from app.models.citation import (
    SourceDocument, 
    SourceLibrary, 
    FinalResponse, 
    CitationMetadata,
    get_page_number
)


def ask_annual_report(store_name: str, question: str) -> Dict[str, Any]:
    """
    Queries the currently loaded Annual Report PDF from the vector store.
    
    Returns a FinalResponse structure as a dictionary with:
        - clean_text: Text WITHOUT citation tags (for reading)
        - cited_text: Text WITH [[Src:xxx]] citation tags
        - citations: List of citation metadata with positions and source IDs
        - sources: Dictionary of SourceDocument objects for tooltips
    """
    if not store_name:
        logger.warning("No Annual Report vector store has been created or is available.")
        return FinalResponse(
            clean_text="Error: No Annual Report vector store has been created or is available.",
            cited_text="Error: No Annual Report vector store has been created or is available.",
            citations=[],
            sources={}
        ).model_dump()

    logger.info(f"🔎 [Tool] Querying Store '{store_name}': {question[:80]}...")
    time.sleep(2)  # To avoid rate limiting issues

    try:
        gemini_client = client.Client(api_key=GEMINI_API_KEY)
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=question,
            config=types.GenerateContentConfig(
                tools=[types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store_name]
                    )
                )],
            )
        )
        
        # ============ PROCESS GROUNDING METADATA ============
        logger.info("=" * 60)
        logger.info("📋 PROCESSING GROUNDING METADATA")
        logger.info("=" * 60)
        
        source_library = SourceLibrary()
        source_counter = 100  # Starting ID for sources
        chunk_to_source_map: Dict[int, str] = {}  # Maps chunk index to source_id
        citations_list = []  # Will hold CitationMetadata objects
        
        tagged_text = ""
        clean_text = ""
        
        # Check if we have candidates
        if response.candidates:
            candidate = response.candidates[0]
            logger.debug(f"📌 Candidate object type: {type(candidate)}")
            
            # Access grounding_metadata
            grounding = getattr(candidate, 'grounding_metadata', None)
            
            if grounding:
                logger.debug(f"🔗 Grounding Metadata type: {type(grounding)}")
                
                # Process grounding_chunks
                grounding_chunks = getattr(grounding, 'grounding_chunks', None)
                
                if grounding_chunks:
                    logger.info(f"✅ Found {len(grounding_chunks)} grounding chunks!")
                    
                    for i, chunk in enumerate(grounding_chunks):
                        source_id = f"src_{source_counter}"
                        source_counter += 1
                        
                        # Get retrieved_context
                        retrieved_context = getattr(chunk, 'retrieved_context', None)
                        if retrieved_context:
                            title = getattr(retrieved_context, 'title', 'Unknown Source')
                            text = getattr(retrieved_context, 'text', '')
                            
                            # Extract page number from chunk text
                            page_number = get_page_number(text)
                            
                            # Create SourceDocument
                            source_doc = SourceDocument(
                                source_id=source_id,
                                title=title,
                                page_number=page_number,
                                raw_text=text[:500] if text else ""  # Store first 500 chars for tooltip
                            )
                            
                            source_library.add_source(source_doc)
                            chunk_to_source_map[i] = source_id
                            
                            logger.debug(f"📄 CHUNK {i}: {source_id}")
                            logger.debug(f"   📑 Title: {title}")
                            logger.debug(f"   📖 Page: {page_number}")
                            logger.debug(f"   📝 Text preview: {text[:100]}...")
                else:
                    logger.warning("⚠️ No grounding_chunks found in grounding_metadata")
                
                # Process grounding_supports to embed citation tags
                grounding_supports = getattr(grounding, 'grounding_supports', None)
                
                if grounding_supports:
                    logger.info(f"📍 Found {len(grounding_supports)} grounding supports (citation markers)")
                    
                    # Build text with citations
                    response_text = response.text if response.text else ""
                    clean_text = response_text  # Original text without tags
                    tagged_text = response_text
                    
                    # We need to insert tags after each supported segment
                    # Process in reverse order to maintain correct indices
                    supports_with_indices = []
                    
                    for support in grounding_supports:
                        segment = getattr(support, 'segment', None)
                        if segment:
                            segment_text = getattr(segment, 'text', '')
                            start_index = getattr(segment, 'start_index', 0)
                            end_index = getattr(segment, 'end_index', 0)
                            
                            # Get source IDs for this support
                            chunk_indices = getattr(support, 'grounding_chunk_indices', [])
                            source_ids = [chunk_to_source_map.get(idx, f"src_{100+idx}") for idx in chunk_indices]
                            
                            logger.debug(f"📌 Support: '{segment_text[:50]}...'")
                            logger.debug(f"   Indices: {start_index}-{end_index}")
                            logger.debug(f"   Sources: {source_ids}")
                            
                            # Create CitationMetadata for each source
                            for sid in source_ids:
                                citation = CitationMetadata(
                                    start_index=start_index,
                                    end_index=end_index,
                                    source_id=sid
                                )
                                citations_list.append(citation)
                                logger.debug(f"📎 Created citation: {start_index}-{end_index} -> {sid}")
                            
                            supports_with_indices.append({
                                'text': segment_text,
                                'start': start_index,
                                'end': end_index,
                                'source_ids': source_ids
                            })
                    
                    # Sort by end index in reverse order
                    supports_with_indices.sort(key=lambda x: x['end'], reverse=True)
                    
                    # Insert tags from end to start (to preserve indices)
                    for support_info in supports_with_indices:
                        if support_info['source_ids']:
                            # Create tag string like [[Src:101]][[Src:102]]
                            tags = ''.join([f"[[Src:{sid.replace('src_', '')}]]" for sid in support_info['source_ids']])
                            # Insert after the segment
                            end_pos = support_info['end']
                            if end_pos <= len(tagged_text):
                                tagged_text = tagged_text[:end_pos] + tags + tagged_text[end_pos:]
                                logger.debug(f"✏️ Inserted tags at position {end_pos}: {tags}")
                    
                    logger.info("✅ Successfully embedded citation tags in response text")
                    
                else:
                    logger.warning("⚠️ No grounding_supports found in grounding_metadata")
                    tagged_text = response.text if response.text else ""
                    clean_text = tagged_text
                    
            else:
                logger.warning("⚠️ No grounding_metadata found on candidate")
                tagged_text = response.text if response.text else ""
                clean_text = tagged_text
        else:
            logger.warning("⚠️ No candidates in response")
            tagged_text = ""
            clean_text = ""
            
        logger.info("=" * 60)
        logger.info("📋 END GROUNDING METADATA PROCESSING")
        logger.info("=" * 60)
        
        # Build FinalResponse
        final_response = FinalResponse(
            clean_text=clean_text,
            cited_text=tagged_text,
            citations=citations_list,
            sources={sid: src for sid, src in source_library.sources.items()}
        )
        
        logger.info(f"📦 Returning FinalResponse with:")
        logger.info(f"   - {len(citations_list)} citations")
        logger.info(f"   - {len(source_library.sources)} sources")
        logger.debug(f"📝 Clean text preview: {clean_text[:200]}...")
        logger.debug(f"📝 Cited text preview: {tagged_text[:200]}...")
        
        # Return as dict for tool compatibility
        return final_response.model_dump()
        
    except Exception as e:
        logger.error(f"Tool Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return FinalResponse(
            clean_text=f"Tool Error: {str(e)}",
            cited_text=f"Tool Error: {str(e)}",
            citations=[],
            sources={}
        ).model_dump()


def exit_loop(callback_context):
    """
    A tool that the CritiqueAgent can call to signal that the report is approved
    and the refinement loop should be terminated.
    """
    logger.info("✅ [Tool] Report approved. Exiting refinement loop.")
    return "Report approved. Exiting loop."
