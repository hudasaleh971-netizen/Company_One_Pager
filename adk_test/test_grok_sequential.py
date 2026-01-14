"""
Test Sequential Extraction Agent with Groq
============================================
Tests the sequential_extraction_agent which uses Groq (via LiteLlm) 
for fast LLM inference instead of Gemini.

This test runs:
1. initial_search_agent (Gemini) - finds/uploads annual report to vector store
2. sequential_extraction_agent (Groq) - runs all 5 extraction agents sequentially
"""

import sys
import os
import asyncio
from pathlib import Path
from google.genai import types
from loguru import logger

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# ============ LOGGING SETUP ============
logger.remove()

# Console logging - colorful output
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG"
)

# File logging - saved to logs directory
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logger.add(
    LOG_DIR / "test_grok_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

logger.info(f"📁 Test logs will be saved to: {LOG_DIR}")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agents.initial_search_agent import initial_search_agent
from app.agents.sequential_extraction_agent import create_sequential_extraction_agent

# CONFIGURATION
APP_NAME = "test_grok_app"
USER_ID = "test_user"
SESSION_ID = "test_grok_sequential"

async def test_grok_sequential_agent():
    """
    Test that runs:
    1. initial_search_agent (Gemini) - finds/uploads annual report to vector store
    2. sequential_extraction_agent (Grok) - runs all 5 extraction agents one at a time
    """
    logger.info("=" * 70)
    logger.info("🧪 GROK SEQUENTIAL AGENT TEST")
    logger.info("   Phase 1: initial_search_agent (Gemini)")
    logger.info("   Phase 2: sequential_extraction_agent (Grok via LiteLlm)")
    logger.info("=" * 70)
    
    # 1. Setup Session Service
    session_service = InMemorySessionService()
    
    # 2. Prepare Initial State
    initial_state = {
        "company_name": "Saksiam",
        "annual_report_filename": "C:/Users/HudaGoian/Documents/Cooperate Development/Company One Pager/Saksiam AR 24.pdf"
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
    # PHASE 1: Run Initial Search Agent (Gemini)
    # ============================================================
    logger.info("-" * 70)
    logger.info("📋 PHASE 1: Running InitialSearchAgent (Gemini)")
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

        event_count = 0
        async for event in events:
            event_count += 1
            author = getattr(event, 'author', 'unknown')
            logger.debug(f"📨 Event #{event_count} from: {author}, is_final: {event.is_final_response()}")
            
            if event.is_final_response():
                logger.info("✅ InitialSearchAgent Result:")
                if event.content and event.content.parts:
                    result_text = event.content.parts[0].text
                    logger.info(f"   Output (first 500 chars): {result_text[:500]}")
    
    except Exception as e:
        logger.error(f"❌ Error in Phase 1: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return

    # Get the updated session to check vector_store_name
    session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    vector_store_name = session.state.get("vector_store_name")
    
    logger.info(f"📦 Vector Store Name from Session: {vector_store_name}")
    
    if not vector_store_name:
        logger.error("❌ No vector store created. Cannot proceed to Phase 2.")
        logger.error(f"   initial_search_output: {session.state.get('initial_search_output', 'NOT FOUND')[:500]}")
        return

    # ============================================================
    # PHASE 2: Run Sequential Extraction Agent (Grok)
    # ============================================================
    logger.info("-" * 70)
    logger.info("📋 PHASE 2: Running SequentialExtractionAgent (Grok)")
    logger.info("-" * 70)
    logger.info("⏳ This will run all 5 extraction agents ONE AT A TIME using Grok")
    logger.info("-" * 70)
    
    # Create fresh sequential agent using factory
    sequential_agent = create_sequential_extraction_agent()
    
    runner2 = Runner(
        agent=sequential_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    try:
        query2 = types.Content(role='user', parts=[types.Part(text="Extract all information from the annual report.")])
        
        events = runner2.run_async(
            user_id=USER_ID, 
            session_id=SESSION_ID, 
            new_message=query2
        )

        event_count = 0
        async for event in events:
            event_count += 1
            author = getattr(event, 'author', 'unknown')
            logger.debug(f"📨 Event #{event_count} from: {author}, is_final: {event.is_final_response()}")
            
            if event.is_final_response():
                logger.info(f"✅ Final response from {author}")
                if event.content and event.content.parts:
                    result_text = event.content.parts[0].text
                    logger.info(f"   Output (first 1000 chars):\n{result_text[:1000]}")
    
    except Exception as e:
        logger.error(f"❌ Error in Phase 2: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # ============================================================
    # SUMMARY
    # ============================================================
    logger.info("=" * 70)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 70)
    
    final_session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    logger.info(f"Company: {final_session.state.get('company_name')}")
    logger.info(f"Vector Store: {final_session.state.get('vector_store_name')}")
    
    # Check all extracted data sections
    #sections = ['leadership_data', 'metrics_data', 'stakeholder_data', 'products_data', 'overview_data']
    sections = ['stakeholder_data']
   
    for section in sections:
        data = final_session.state.get(section)
        if data:
            logger.info(f"✅ {section}: Found in session state")
            if isinstance(data, str):
                logger.debug(f"   First 500 chars: {data[:500]}")
            elif isinstance(data, dict):
                import json
                logger.debug(f"   Keys: {list(data.keys())}")
        else:
            logger.warning(f"⚠️ {section}: Not in state")
    
    logger.info("=" * 70)
    logger.info("🏁 TEST COMPLETE")
    logger.info("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_grok_sequential_agent())
