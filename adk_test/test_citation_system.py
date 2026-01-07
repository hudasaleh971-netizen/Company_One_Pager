"""
Test Citation System

This test file runs:
1. initial_search_agent - finds/uploads annual report to vector store
2. stakeholder_agent - queries the vector store for stakeholder info with citations

This test verifies that grounding metadata is properly captured and [[Src:xxx]] tags
are embedded in the response text.
"""

import sys
import os
import asyncio
from google.genai import types
from loguru import logger

# Configure loguru for detailed output
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG"
)

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agents.initial_search_agent import initial_search_agent
from app.agents.parallel_extraction_agent import stakeholder_agent

# CONFIGURATION
APP_NAME = "test_citation_app"
USER_ID = "test_user"
SESSION_ID = "test_citation_system"


async def test_citation_system():
    """
    Test that runs:
    1. initial_search_agent - finds/uploads annual report to vector store
    2. stakeholder_agent - queries the vector store for stakeholder info
    
    This test prints grounding metadata and verifies citation tags are embedded.
    """
    logger.info("=" * 70)
    logger.info("🧪 CITATION SYSTEM TEST: initial_search_agent → stakeholder_agent")
    logger.info("=" * 70)
    
    # 1. Setup Session Service
    session_service = InMemorySessionService()
    
    # 2. Prepare Initial State
    # Change these values to test with different companies/files
    initial_state = {
        "company_name": "Saksiam",
        "annual_report_filename": "C:/Users/HudaGoian/Documents/Cooperate Development/Company One Pager/Company_One_Pager/Saksiam_annual_report.pdf"
    }
    
    # 3. Create the Session with Initial State
    logger.info(f"📝 Creating session with state:")
    logger.info(f"   company_name: {initial_state['company_name']}")
    logger.info(f"   annual_report_filename: {initial_state['annual_report_filename']}")
    
    session = await session_service.create_session(
        app_name=APP_NAME, 
        user_id=USER_ID, 
        session_id=SESSION_ID,
        state=initial_state
    )

    # ============================================================
    # PHASE 1: Run Initial Search Agent
    # ============================================================
    logger.info("-" * 70)
    logger.info("📋 PHASE 1: Running InitialSearchAgent")
    logger.info("-" * 70)
    
    runner1 = Runner(
        agent=initial_search_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    try:
        query1 = types.Content(role='user', parts=[types.Part(text="Find the annual report.")])
        
        events = runner1.run_async(
            user_id=USER_ID, 
            session_id=SESSION_ID, 
            new_message=query1
        )

        async for event in events:
            if event.is_final_response():
                logger.info("✅ InitialSearchAgent Result:")
                if event.content and event.content.parts:
                    logger.info(event.content.parts[0].text)
    
    except Exception as e:
        logger.error(f"❌ Error in Phase 1: {e}")
        import traceback
        traceback.print_exc()
        return

    # Get the updated session to check vector_store_name
    session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    vector_store_name = session.state.get("vector_store_name")
    
    logger.info(f"📦 Vector Store Name from Session: {vector_store_name}")
    
    if not vector_store_name:
        logger.error("❌ No vector store created. Cannot proceed to Phase 2.")
        return

    # ============================================================
    # PHASE 2: Run Stakeholder Agent
    # ============================================================
    logger.info("-" * 70)
    logger.info("📋 PHASE 2: Running StakeholderAgent")
    logger.info("-" * 70)
    logger.info("⏳ This will query the vector store and process GROUNDING METADATA")
    logger.info("-" * 70)
    
    runner2 = Runner(
        agent=stakeholder_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    try:
        query2 = types.Content(role='user', parts=[types.Part(text="List all known shareholders with their ownership percentages.")])
        
        events = runner2.run_async(
            user_id=USER_ID, 
            session_id=SESSION_ID, 
            new_message=query2
        )

        async for event in events:
            if event.is_final_response():
                logger.info("✅ StakeholderAgent Result:")
                if event.content and event.content.parts:
                    result_text = event.content.parts[0].text
                    
                    # Try to parse as JSON (new CitedContent schema)
                    import json
                    try:
                        parsed = json.loads(result_text)
                        content = parsed.get("content", result_text)
                        has_citations = parsed.get("has_citations", False)
                        logger.info(f"📋 Parsed structured output: has_citations={has_citations}")
                    except json.JSONDecodeError:
                        content = result_text
                        has_citations = False
                        logger.warning("⚠️ Could not parse as JSON, using raw text")
                    
                    # Check for citation tags
                    import re
                    citation_tags = re.findall(r'\[\[Src:\d+\]\]', content)
                    
                    logger.info("-" * 50)
                    logger.info("📊 CITATION ANALYSIS:")
                    logger.info(f"   has_citations flag: {has_citations}")
                    logger.info(f"   Found {len(citation_tags)} citation tags in response")
                    if citation_tags:
                        logger.info(f"   Tags: {citation_tags[:10]}...")  # Show first 10
                    logger.info("-" * 50)
                    
                    # Print the result (truncated if too long)
                    if len(content) > 2000:
                        logger.info(content[:2000] + "...")
                    else:
                        logger.info(content)
    
    except Exception as e:
        logger.error(f"❌ Error in Phase 2: {e}")
        import traceback
        traceback.print_exc()

    # ============================================================
    # SUMMARY
    # ============================================================
    logger.info("=" * 70)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 70)
    
    final_session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    logger.info(f"Company: {final_session.state.get('company_name')}")
    logger.info(f"Vector Store: {final_session.state.get('vector_store_name')}")
    logger.info(f"Stakeholder Data: {'✅ Found' if final_session.state.get('stakeholder_data') else '⚠️ Not in state'}")
    
    logger.info("=" * 70)
    logger.info("🏁 TEST COMPLETE")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_citation_system())
