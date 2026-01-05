import sys
import os
import asyncio
from google.genai import types

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agents.initial_search_agent import initial_search_agent

# CONFIGURATION
APP_NAME = "test_app"
USER_ID = "test_user"
SESSION_ID = "test_session_01"

async def test_initial_search():
    print("--- Testing Initial Search Agent (Runner Mode) ---")
    
    # 1. Setup Session Service
    # We use InMemorySessionService to hold state during the test
    session_service = InMemorySessionService()
    
    # 2. Prepare Initial State
    # The agent's instruction uses template syntax (e.g., {{company_name}}) which the ADK
    # replaces with values from the session state at runtime.
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
    # We pass the SAME session_service so the Runner finds our session with the state.
    runner = Runner(
        agent=initial_search_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    print(f"Agent: {initial_search_agent.name}")
    
    try:
        query_content = types.Content(role='user', parts=[types.Part(text="Find the annual report.")])
        
        print("\n--- Running Agent ---")
        
        # 5. RUN WITHOUT context_variables
        # The Runner automatically pulls state from the session we created.
        events = runner.run_async(
            user_id=USER_ID, 
            session_id=SESSION_ID, 
            new_message=query_content
        )

        

        async for event in events:
            if event.is_final_response():
                print("\n--- Result ---")
                if event.content and event.content.parts:
                    print(event.content.parts[0].text)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_initial_search())