"""
Sequential Extraction Test
===========================
Run extraction agents ONE AT A TIME on existing file store.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agents.sequential_extraction_agent import create_sequential_extraction_agent

# ============================================================
# CONFIGURATION
# ============================================================
STORE_NAME = "fileSearchStores/saksiam-store-x9i0i8eds9ex"
COMPANY_NAME = "Saksiam"

print(f"✅ Sequential mode - agents run one at a time")
print(f"🗄️ Store: {STORE_NAME}")

# ============================================================
# RUN SEQUENTIAL EXTRACTION
# ============================================================
async def run_extraction():
    """Run sequential extraction on existing file store."""
    
    session_service = InMemorySessionService()
    
    await session_service.create_session(
        app_name="test",
        user_id="user",
        session_id="session",
        state={
            "company_name": COMPANY_NAME,
            "vector_store_name": STORE_NAME
        }
    )
    
    agent = create_sequential_extraction_agent()
    runner = Runner(agent=agent, app_name="test", session_service=session_service)
    
    print(f"\n⏳ Running 5 agents SEQUENTIALLY on {COMPANY_NAME}...")
    print("(This is slower but avoids rate limits)\n")
    
    query = types.Content(role='user', parts=[types.Part(text="Extract company information.")])
    events = runner.run_async(user_id="user", session_id="session", new_message=query)
    
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            print(f"\n✅ Done!\n{event.content.parts[0].text[:1000]}")
    
    # Get results from session state
    session = await session_service.get_session(app_name="test", user_id="user", session_id="session")
    
    print("\n📊 Extracted Data:")
    for key in ["leadership_data", "metrics_data", "stakeholder_data", "products_data", "overview_data"]:
        data = session.state.get(key)
        print(f"  {key}: {'✅' if data else '❌'}")
    
    return session.state

# ============================================================
# EXECUTE - Uncomment to run
# ============================================================
# results = await run_extraction()
