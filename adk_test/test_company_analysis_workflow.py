import sys
import os
import asyncio
from google.genai import types

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agents.company_analysis_workflow import company_analysis_workflow

# CONFIGURATION
APP_NAME = "test_app"
USER_ID = "test_user"
SESSION_ID = "test_session_workflow"

async def test_company_analysis_workflow():
    print("--- Testing Company Analysis Workflow (Runner Mode) ---")
    
    # 1. Setup Session Service
    session_service = InMemorySessionService()
    
    # 2. Prepare Initial State

    initial_state = {
        "company_name": "Saksiam",
        "annual_report_filename": "C:/Users/HudaGoian/Documents/Cooperate Development/Company One Pager/Saksiam AR 24.pdf"  # Use string "None" for safe template rendering
    }
    
    # 3. Create the Session with Initial State
    print(f"Creating session: {SESSION_ID} with initial state...")
    session = await session_service.create_session(
        app_name=APP_NAME, 
        user_id=USER_ID, 
        session_id=SESSION_ID,
        state=initial_state
    )

    # Verify state is set
    print(f"Current Session State: {session.state}")

    # 4. Initialize Runner
    runner = Runner(
        agent=company_analysis_workflow,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    print(f"Agent: {company_analysis_workflow.name}")
    
    try:
        query_content = types.Content(role='user', parts=[types.Part(text="Analyze the company based on its latest annual report.")])
        
        print("\n--- Running Workflow ---")
        
        events = runner.run_async(
            user_id=USER_ID, 
            session_id=SESSION_ID, 
            new_message=query_content
        )

        async for event in events:
            if event.is_final_response():
                print("\n--- Final Result ---")
                if event.content and event.content.parts:
                    print(event.content.parts[0].text)
        
        # 6. Verify Output in Session State
        final_session = await session_service.get_session(SESSION_ID)
        
        print("\n--- Verification ---")
        if final_session.state.get("compiled_report"):
             print(f"✅ SUCCESS: Compiled report found in session state.")
        else:
             print(f"⚠️ Report NOT found.")
             print(f"Final State Dump: {final_session.state}")
             
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_company_analysis_workflow())
