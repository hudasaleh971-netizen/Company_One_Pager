"""
Agent Runner Module

Runs the citation agents and returns a FinalResponse.
"""

import sys
import os
import asyncio
from typing import Optional

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from loguru import logger

from app.agents.initial_search_agent import initial_search_agent
from app.agents.parallel_extraction_agent import stakeholder_agent
from app.models.citation import FinalResponse


async def run_analysis(
    company_name: str, 
    file_path: Optional[str] = None
) -> dict:
    """
    Run the citation agents for a company.
    
    Args:
        company_name: Name of the company to analyze
        file_path: Optional path to the annual report PDF
        
    Returns:
        Dictionary with the agent output including citations
    """
    logger.info(f"🚀 Starting analysis for: {company_name}")
    
    APP_NAME = "citation_ui"
    USER_ID = "ui_user"
    SESSION_ID = f"session_{company_name.lower().replace(' ', '_')}"
    
    # Setup session
    session_service = InMemorySessionService()
    
    initial_state = {
        "company_name": company_name,
        "annual_report_filename": file_path or ""
    }
    
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state=initial_state
    )
    
    # Phase 1: Run Initial Search Agent
    logger.info("📋 Phase 1: Running InitialSearchAgent...")
    
    runner1 = Runner(
        agent=initial_search_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    try:
        query1 = types.Content(role='user', parts=[types.Part(text="Find the annual report.")])
        events = runner1.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=query1)
        
        async for event in events:
            if event.is_final_response():
                logger.info("✅ InitialSearchAgent completed")
                
    except Exception as e:
        logger.error(f"❌ Error in Phase 1: {e}")
        return {"error": str(e)}
    
    # Check vector store was created
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    vector_store_name = session.state.get("vector_store_name")
    
    if not vector_store_name:
        logger.error("❌ No vector store created")
        return {"error": "Failed to create vector store for annual report"}
    
    logger.info(f"📦 Vector Store: {vector_store_name}")
    
    # Phase 2: Run Stakeholder Agent
    logger.info("📋 Phase 2: Running StakeholderAgent...")
    
    runner2 = Runner(
        agent=stakeholder_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    result = {
        "company_name": company_name,
        "content": "",
        "sources": {},
        "has_citations": False
    }
    
    try:
        query2 = types.Content(role='user', parts=[types.Part(
            text="List all known shareholders with their ownership percentages and notes."
        )])
        
        events = runner2.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=query2)
        
        async for event in events:
            if event.is_final_response():
                if event.content and event.content.parts:
                    raw_output = event.content.parts[0].text
                    
                    # Try to parse as JSON (from CitedContent schema)
                    import json
                    try:
                        parsed = json.loads(raw_output)
                        result["content"] = parsed.get("content", raw_output)
                        result["sources"] = parsed.get("sources", {})
                        result["has_citations"] = parsed.get("has_citations", False)
                    except json.JSONDecodeError:
                        result["content"] = raw_output
                    
                    logger.info("✅ StakeholderAgent completed")
                    
    except Exception as e:
        logger.error(f"❌ Error in Phase 2: {e}")
        return {"error": str(e)}
    
    # Check for citations in the content
    import re
    citation_tags = re.findall(r'\[\[Src:(\d+)\]\]', result["content"])
    result["citation_count"] = len(citation_tags)
    
    logger.info(f"📊 Analysis complete: {result['citation_count']} citations found")
    
    return result


def run_sync(company_name: str, file_path: Optional[str] = None) -> dict:
    """Synchronous wrapper for run_analysis."""
    return asyncio.run(run_analysis(company_name, file_path))


if __name__ == "__main__":
    # Test run
    result = run_sync("Saksiam", "C:/Users/HudaGoian/Documents/Cooperate Development/Company One Pager/Company_One_Pager/Saksiam_annual_report.pdf")
    print(result)
