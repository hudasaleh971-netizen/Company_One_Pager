import sys
import os
import asyncio
from pathlib import Path
from google.genai import types
from loguru import logger
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agents.initial_search_agent import initial_search_agent
from app.agents.parallel_extraction_agent import leadership_agent
# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Verify Google Application Credentials are set
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    logger.error("❌ GOOGLE_APPLICATION_CREDENTIALS environment variable is not set!")
    logger.error("   Please set it to your service account JSON key file path.")
    logger.error("   Example: $env:GOOGLE_APPLICATION_CREDENTIALS = 'C:/path/to/key.json'")
    sys.exit(1)
else:
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    logger.info(f"✅ Using credentials from: {creds_path}")
    if not os.path.exists(creds_path):
        logger.warning(f"⚠️ Credentials file not found at: {creds_path}")

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
    LOG_DIR / "test_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

logger.info(f"📁 Test logs will be saved to: {LOG_DIR}")



# CONFIGURATION
APP_NAME = "test_app"
USER_ID = "test_user"
SESSION_ID = "test_sequential_agents"

async def test_sequential_agents():
    """
    Test that runs:
    1. initial_search_agent - finds/uploads annual report to vector store
    2. leadership_agent - queries the vector store for leadership info
    
    This test prints grounding metadata to help understand citation sources.
    """
    logger.info("=" * 70)
    logger.info("🧪 SEQUENTIAL AGENT TEST: initial_search_agent → leadership_agent")
    logger.info("=" * 70)
    
    # 1. Setup Session Service
    session_service = InMemorySessionService()
    
    # 2. Prepare Initial State
    # Change these values to test with different companies/files
    initial_state = {
        "company_name": "Saksiam",
        "annual_report_filename": "C:/Users/HudaGoian/Documents/Cooperate Development/Company One Pager/Saksiam AR 24.pdf"  # Use string "None" for safe template rendering
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
                    logger.debug(f"   Full output: {result_text}")
    
    except Exception as e:
        logger.error(f"❌ Error in Phase 1: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return

    # Get the updated session to check vector_store_name
    session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    vector_store_name = session.state.get("vector_store_name")
    
    logger.info(f"📦 Vector Store Name from Session: {vector_store_name}")
    logger.debug(f"📋 Session state keys: {list(session.state.keys())}")
    
    if not vector_store_name:
        logger.error("❌ No vector store created. Cannot proceed to Phase 2.")
        logger.error(f"   initial_search_output: {session.state.get('initial_search_output', 'NOT FOUND')[:500]}")
        return

    # ============================================================
    # PHASE 2: Run Leadership Agent
    # ============================================================
    logger.info("-" * 70)
    logger.info("📋 PHASE 2: Running LeadershipAgent")
    logger.info("-" * 70)
    logger.info("⏳ This will query the vector store and extract leadership info")
    logger.info("-" * 70)
    
    runner2 = Runner(
        agent=leadership_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    try:
        query2 = types.Content(role='user', parts=[types.Part(text="Extract the management team information.")])
        
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
                logger.info("✅ LeadershipAgent Result:")
                if event.content and event.content.parts:
                    result_text = event.content.parts[0].text
                    # Log first 2000 chars to console/file
                    logger.info(f"   Output (first 2000 chars):\n{result_text[:2000]}")
                    if len(result_text) > 2000:
                        logger.debug(f"   Full output ({len(result_text)} chars):\n{result_text}")
    
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
    
    leadership_data = final_session.state.get('leadership_data')
    if leadership_data:
        logger.info("Leadership Data: ✅ Found in session state")
        # Display the data (it's stored by output_key)
        if isinstance(leadership_data, str):
            logger.info(f"📋 Leadership Data (first 1500 chars):")
            logger.info(leadership_data[:1500] + "..." if len(leadership_data) > 1500 else leadership_data)
            logger.debug(f"📋 Full Leadership Data:\n{leadership_data}")
        elif isinstance(leadership_data, dict):
            import json
            formatted = json.dumps(leadership_data, indent=2)
            logger.info(f"📋 Leadership Data (structured - first 1500 chars):")
            logger.info(formatted[:1500])
            logger.debug(f"📋 Full Leadership Data:\n{formatted}")
    else:
        logger.warning("Leadership Data: ⚠️ Not in state")
        logger.warning(f"   Available keys: {list(final_session.state.keys())}")
    
    logger.info("=" * 70)
    logger.info("🏁 TEST COMPLETE")
    logger.info("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_sequential_agents())

