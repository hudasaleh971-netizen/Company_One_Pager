import sys
import os
import asyncio
from google.genai import types

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agents.initial_search_agent import initial_search_agent
from app.agents.parallel_extraction_agent import leadership_agent

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
    print("\n" + "="*70)
    print("🧪 SEQUENTIAL AGENT TEST: initial_search_agent → leadership_agent")
    print("="*70)
    
    # 1. Setup Session Service
    session_service = InMemorySessionService()
    
    # 2. Prepare Initial State
    # Change these values to test with different companies/files
    initial_state = {
        "company_name": "Saksiam",
        "annual_report_filename": "C:/Users/HudaGoian/Documents/Cooperate Development/Company One Pager/Company_One_Pager/Saksiam_annual_report.pdf"
    }
    
    # 3. Create the Session with Initial State
    print(f"\n📝 Creating session with state:")
    print(f"   company_name: {initial_state['company_name']}")
    print(f"   annual_report_filename: {initial_state['annual_report_filename']}")
    
    session = await session_service.create_session(
        app_name=APP_NAME, 
        user_id=USER_ID, 
        session_id=SESSION_ID,
        state=initial_state
    )

    # ============================================================
    # PHASE 1: Run Initial Search Agent
    # ============================================================
    print("\n" + "-"*70)
    print("📋 PHASE 1: Running InitialSearchAgent")
    print("-"*70)
    
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
                print("\n✅ InitialSearchAgent Result:")
                if event.content and event.content.parts:
                    print(event.content.parts[0].text)
    
    except Exception as e:
        print(f"❌ Error in Phase 1: {e}")
        import traceback
        traceback.print_exc()
        return

    # Get the updated session to check vector_store_name
    session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    vector_store_name = session.state.get("vector_store_name")
    
    print(f"\n📦 Vector Store Name from Session: {vector_store_name}")
    
    if not vector_store_name:
        print("❌ No vector store created. Cannot proceed to Phase 2.")
        return

    # ============================================================
    # PHASE 2: Run Leadership Agent
    # ============================================================
    print("\n" + "-"*70)
    print("📋 PHASE 2: Running LeadershipAgent")
    print("-"*70)
    print("⏳ This will query the vector store and print GROUNDING METADATA")
    print("-"*70)
    
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

        async for event in events:
            if event.is_final_response():
                print("\n✅ LeadershipAgent Result:")
                if event.content and event.content.parts:
                    result_text = event.content.parts[0].text
                    print(result_text[:2000] + "..." if len(result_text) > 2000 else result_text)
    
    except Exception as e:
        print(f"❌ Error in Phase 2: {e}")
        import traceback
        traceback.print_exc()

    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    final_session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    print(f"Company: {final_session.state.get('company_name')}")
    print(f"Vector Store: {final_session.state.get('vector_store_name')}")
    print(f"Leadership Data: {'✅ Found' if final_session.state.get('leadership_data') else '⚠️ Not in state'}")
    
    print("\n" + "="*70)
    print("🏁 TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_sequential_agents())
