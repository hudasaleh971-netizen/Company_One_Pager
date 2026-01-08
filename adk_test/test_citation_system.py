"""
Test Citation System with SequentialAgent

Uses factory functions to create fresh agent instances.
Logs FinalResponse to file: logs/test_citation_YYYY-MM-DD.log
"""

import sys
import os
import asyncio
import re
import json
from pathlib import Path
from google.genai import types
from loguru import logger

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# ============ LOGGING SETUP ============
logger.remove()

logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG"
)

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger.add(
    LOG_DIR / "test_citation_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

logger.info(f"📁 Logs: {LOG_DIR}")

from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Import factory functions (not instances)
from app.agents.initial_search_agent import create_initial_search_agent
from app.agents.parallel_extraction_agent import create_stakeholder_agent
from app.models.citation import FinalResponse, CitationMetadata, SourceDocument, extract_citations_from_tags

# CONFIGURATION
APP_NAME = "test_citation_app"
USER_ID = "test_user"
SESSION_ID = "test_citation_sequential"


def create_citation_sequential_agent() -> SequentialAgent:
    """Factory to create a fresh SequentialAgent for citation testing."""
    return SequentialAgent(
        name="CitationSequentialAgent",
        sub_agents=[
            create_initial_search_agent("CitationInitialSearchAgent"),
            create_stakeholder_agent("CitationStakeholderAgent"),
        ],
    )



async def test_citation_system():
    """
    Test SequentialAgent: initial_search → stakeholder
    Uses factory functions to create fresh instances.
    """
    logger.info("=" * 70)
    logger.info("🧪 CITATION SYSTEM TEST: SequentialAgent (Factory Functions)")
    logger.info("=" * 70)
    
    session_service = InMemorySessionService()
    
    initial_state = {
        "company_name": "Saksiam",
        "annual_report_filename": "C:/Users/HudaGoian/Documents/Cooperate Development/Company One Pager/Company_One_Pager/Saksiam_annual_report.pdf"
    }
    
    logger.info(f"📝 Session state:")
    logger.info(f"   company_name: {initial_state['company_name']}")
    logger.info(f"   annual_report_filename: {initial_state['annual_report_filename']}")
    
    await session_service.create_session(
        app_name=APP_NAME, 
        user_id=USER_ID, 
        session_id=SESSION_ID,
        state=initial_state
    )

    # Create fresh agent using factory
    citation_agent = create_citation_sequential_agent()
    
    logger.info("-" * 70)
    logger.info(f"📋 Running {citation_agent.name}")
    logger.info("-" * 70)
    
    runner = Runner(
        agent=citation_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    final_response = None
    
    try:
        query = types.Content(
            role='user', 
            parts=[types.Part(text="Find the annual report and list all known shareholders with their ownership percentages.")]
        )
        
        events = runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=query)

        async for event in events:
            if hasattr(event, 'author') and event.author:
                logger.debug(f"📨 Event from: {event.author}")
            
            if event.is_final_response():
                logger.info("=" * 70)
                logger.info("✅ Final Result:")
                logger.info("=" * 70)
                
                if event.content and event.content.parts:
                    raw_output = event.content.parts[0].text
                    logger.info(f"📝 Raw output: {len(raw_output)} chars")
                    logger.debug(f"{raw_output[:500]}...")
                    
                    # Try to parse JSON
                    cited_text = raw_output
                    sources_raw = {}
                    try:
                        parsed = json.loads(raw_output)
                        cited_text = parsed.get("content", raw_output)
                        sources_raw = parsed.get("sources", {})
                        logger.info(f"✅ Parsed JSON: {len(sources_raw)} sources")
                    except json.JSONDecodeError:
                        logger.warning("⚠️ Raw text (not JSON)")
                    
                    # Use shared parser from citation.py
                    clean_text, citations = extract_citations_from_tags(cited_text)
                    
                    # Convert sources
                    sources = {}
                    for src_id, src_data in sources_raw.items():
                        if isinstance(src_data, dict):
                            sources[src_id] = SourceDocument(
                                source_id=src_id,
                                title=src_data.get("title", "Annual Report"),
                                page_number=src_data.get("page_number", ""),
                                raw_text=src_data.get("raw_text", "")[:500]
                            )
                    
                    # Create FinalResponse
                    final_response = FinalResponse(
                        clean_text=clean_text,
                        cited_text=cited_text,
                        citations=citations,
                        sources=sources
                    )
                    
                    # Log FinalResponse
                    logger.info("=" * 70)
                    logger.info("📦 FINAL RESPONSE:")
                    logger.info("=" * 70)
                    logger.info(f"clean_text: {len(clean_text)} chars")
                    logger.info(f"cited_text: {len(cited_text)} chars")
                    logger.info(f"citations: {len(citations)}")
                    logger.info(f"sources: {len(sources)}")
                    
                    # Sample citations
                    for i, cit in enumerate(citations[:3]):
                        logger.info(f"  [{i+1}] {cit.source_id} at {cit.start_index}")
                    
                    # JSON dump
                    logger.info("\n📋 JSON:")
                    logger.info(json.dumps(final_response.model_dump(), indent=2, default=str)[:1500])
                    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return

    # Summary
    logger.info("=" * 70)
    logger.info("📊 SUMMARY")
    logger.info("=" * 70)
    
    final_session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    logger.info(f"Vector Store: {final_session.state.get('vector_store_name')}")
    logger.info(f"FinalResponse: {'✅' if final_response else '❌'}")
    if final_response:
        logger.info(f"  Citations: {len(final_response.citations)}")
    
    logger.info("=" * 70)
    logger.info(f"🏁 DONE - Logs: {LOG_DIR}")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_citation_system())
