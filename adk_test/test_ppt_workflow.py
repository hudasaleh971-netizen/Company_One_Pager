"""
PPT Workflow Test Script
=========================
Tests the PPT Company Analysis Workflow end-to-end.
Runs extraction and generates PowerPoint slides.
"""

import sys
import os
import asyncio
from pathlib import Path
from google.genai import types
from loguru import logger
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app.agents.ppt_workflow import create_ppt_workflow

# Verify Google Application Credentials
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    logger.error("❌ GOOGLE_APPLICATION_CREDENTIALS not set!")
    sys.exit(1)
else:
    logger.info(f"✅ Using credentials from: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")

# ============ LOGGING SETUP ============
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG"
)

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logger.add(
    LOG_DIR / "test_ppt_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Test Configuration
APP_NAME = "ppt_test_app"
USER_ID = "test_user"
SESSION_ID = "test_ppt_workflow"


async def test_ppt_workflow():
    """
    Run the PPT Company Analysis Workflow end-to-end.
    
    This test:
    1. Creates the PPT workflow (Sequential Extraction + PPT generation)
    2. Runs it against a sample annual report
    3. Verifies the PPT is generated in outputs/
    """
    logger.info("=" * 70)
    logger.info("🧪 PPT WORKFLOW TEST")
    logger.info("=" * 70)
    
    # Setup
    session_service = InMemorySessionService()
    
    # Configure initial state - UPDATE THESE VALUES FOR YOUR TEST
    initial_state = {
        "company_name": "Saksiam",
        "annual_report_filename": "C:/Users/HudaGoian/Documents/Cooperate Development/Company One Pager/Company_One_Pager/Saksiam_annual_report.pdf"
    }
    
    logger.info(f"📝 Test Configuration:")
    logger.info(f"   Company: {initial_state['company_name']}")
    logger.info(f"   Report: {initial_state['annual_report_filename']}")
    
    # Create session
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state=initial_state
    )
    
    # Create the PPT workflow
    workflow = create_ppt_workflow()
    
    logger.info("-" * 70)
    logger.info("🚀 Starting PPT Workflow...")
    logger.info("-" * 70)
    
    runner = Runner(
        agent=workflow,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    try:
        query = types.Content(
            role='user',
            parts=[types.Part(text="Analyze the annual report and generate a one-pager PPT.")]
        )
        
        events = runner.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=query
        )
        
        event_count = 0
        async for event in events:
            event_count += 1
            author = getattr(event, 'author', 'unknown')
            logger.debug(f"📨 Event #{event_count} from: {author}")
            
            if event.is_final_response():
                logger.info(f"✅ Final response from: {author}")
                if event.content and event.content.parts:
                    result = event.content.parts[0].text
                    logger.info(f"   Result preview: {result[:500]}...")
        
        logger.info(f"📊 Total events processed: {event_count}")
        
    except Exception as e:
        logger.error(f"❌ Workflow Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Check results
    logger.info("=" * 70)
    logger.info("📊 TEST RESULTS")
    logger.info("=" * 70)
    
    final_session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    
    # Check for slide_data
    slide_data = final_session.state.get("slide_data")
    if slide_data:
        logger.info("✅ slide_data: Found in session state")
        if isinstance(slide_data, dict):
            logger.info(f"   Company: {slide_data.get('COMPANY_NAME', 'N/A')}")
            logger.info(f"   Country: {slide_data.get('COUNTRY', 'N/A')}")
    else:
        logger.warning("⚠️ slide_data: Not found in session state")
    
    # Check for PPT output
    ppt_path = final_session.state.get("ppt_output_path")
    if ppt_path:
        logger.info(f"✅ PPT Generated: {ppt_path}")
        if os.path.exists(ppt_path):
            size = os.path.getsize(ppt_path)
            logger.info(f"   File size: {size} bytes")
        else:
            logger.warning(f"   ⚠️ File not found at: {ppt_path}")
    else:
        logger.warning("⚠️ ppt_output_path: Not found in session state")
    
    # List outputs directory
    outputs_dir = Path(__file__).parent.parent / "outputs"
    if outputs_dir.exists():
        ppt_files = list(outputs_dir.glob("*.pptx"))
        logger.info(f"📁 Output files: {len(ppt_files)} PPT files in outputs/")
        for f in ppt_files[-5:]:  # Show last 5
            logger.info(f"   - {f.name}")
    
    logger.info("=" * 70)
    logger.info("🏁 TEST COMPLETE")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_ppt_workflow())
