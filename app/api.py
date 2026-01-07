"""
FastAPI Backend for Citation UI

This is the main API server located in the app folder.
Uses the working agent flow from test_citation_system.py.
"""

import os
import sys
import shutil
import uuid
import asyncio
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from app.agents.initial_search_agent import initial_search_agent
from app.agents.parallel_extraction_agent import stakeholder_agent

# ============ LOGGING SETUP ============
# Remove default handler and configure file + console logging
logger.remove()

# Console output
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG"
)

# File output - saves to logs folder
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logger.add(
    LOG_DIR / "api_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

logger.info(f"📁 Logs will be saved to: {LOG_DIR}")

# ============ UPLOAD DIRECTORY ============
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
logger.info(f"📁 Uploads directory: {UPLOAD_DIR}")

# ============ FASTAPI APP ============
app = FastAPI(
    title="Citation Analysis API",
    description="API for running company analysis with citation support",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalysisResponse(BaseModel):
    company_name: str
    content: str
    sources: dict
    has_citations: bool
    citation_count: int
    error: Optional[str] = None


@app.get("/")
async def root():
    return {"message": "Citation Analysis API", "status": "running"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_company(
    company_name: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    """
    Analyze a company from its annual report.
    
    - **company_name**: Name of the company
    - **file**: Optional PDF file of the annual report
    """
    logger.info("=" * 60)
    logger.info(f"📥 Received analysis request for: {company_name}")
    
    file_path = None
    
    # Handle file upload
    if file:
        # Generate unique filename with original extension
        file_ext = os.path.splitext(file.filename)[1] or ".pdf"
        unique_filename = f"{company_name.replace(' ', '_')}_{uuid.uuid4().hex[:8]}{file_ext}"
        file_path = str(UPLOAD_DIR / unique_filename)
        
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            file_size = os.path.getsize(file_path)
            logger.info(f"📁 Saved uploaded file: {file_path} ({file_size} bytes)")
            
            # Verify file exists
            if not os.path.exists(file_path):
                logger.error(f"❌ File save failed - file not found: {file_path}")
                raise HTTPException(status_code=500, detail="Failed to save uploaded file")
                
        except Exception as e:
            logger.error(f"❌ Failed to save file: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")
    
    # Run analysis
    try:
        result = await run_agents(company_name, file_path)
        
        if "error" in result:
            logger.error(f"❌ Analysis failed: {result['error']}")
            return AnalysisResponse(
                company_name=company_name,
                content="",
                sources={},
                has_citations=False,
                citation_count=0,
                error=result["error"]
            )
        
        logger.info(f"✅ Analysis complete: {result.get('citation_count', 0)} citations found")
        
        return AnalysisResponse(
            company_name=result.get("company_name", company_name),
            content=result.get("content", ""),
            sources=result.get("sources", {}),
            has_citations=result.get("has_citations", False),
            citation_count=result.get("citation_count", 0)
        )
        
    except Exception as e:
        logger.error(f"❌ Analysis exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def run_agents(company_name: str, file_path: Optional[str] = None) -> dict:
    """
    Run the citation agents for a company.
    Based on the working test_citation_system.py flow.
    """
    logger.info(f"🚀 Starting agent pipeline for: {company_name}")
    if file_path:
        logger.info(f"📄 File path: {file_path}")
        logger.info(f"📄 File exists: {os.path.exists(file_path)}")
    
    APP_NAME = "citation_api"
    USER_ID = "api_user"
    SESSION_ID = f"session_{company_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
    
    # Setup session
    session_service = InMemorySessionService()
    
    initial_state = {
        "company_name": company_name,
        "annual_report_filename": file_path if file_path else ""
    }
    
    logger.info(f"📝 Creating session with state: {initial_state}")
    
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state=initial_state
    )
    
    # ============ PHASE 1: Initial Search Agent ============
    logger.info("-" * 50)
    logger.info("📋 PHASE 1: Running InitialSearchAgent")
    logger.info("-" * 50)
    
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
                if event.content and event.content.parts:
                    logger.info(f"✅ InitialSearchAgent response: {event.content.parts[0].text[:200]}...")
                else:
                    logger.info("✅ InitialSearchAgent completed (no content)")
                
    except Exception as e:
        logger.error(f"❌ Error in Phase 1: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": f"InitialSearchAgent failed: {str(e)}"}
    
    # Check vector store was created
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    vector_store_name = session.state.get("vector_store_name")
    
    logger.info(f"📦 Vector Store Name: {vector_store_name}")
    
    if not vector_store_name:
        logger.error("❌ No vector store created")
        logger.error(f"Session state: {dict(session.state)}")
        return {"error": "Failed to create vector store for annual report. Check if file was uploaded correctly."}
    
    # ============ PHASE 2: Stakeholder Agent ============
    logger.info("-" * 50)
    logger.info("📋 PHASE 2: Running StakeholderAgent")
    logger.info("-" * 50)
    
    runner2 = Runner(
        agent=stakeholder_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    result = {
        "company_name": company_name,
        "content": "",
        "sources": {},
        "has_citations": False,
        "citation_count": 0
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
                    logger.info(f"📝 Raw StakeholderAgent output: {raw_output[:300]}...")
                    
                    # Try to parse as JSON (from CitedContent schema)
                    import json
                    try:
                        parsed = json.loads(raw_output)
                        result["content"] = parsed.get("content", raw_output)
                        result["sources"] = parsed.get("sources", {})
                        result["has_citations"] = parsed.get("has_citations", False)
                        logger.info(f"✅ Parsed as JSON, sources: {len(result['sources'])}")
                    except json.JSONDecodeError:
                        result["content"] = raw_output
                        logger.warning("⚠️ Could not parse as JSON, using raw text")
                    
                    logger.info("✅ StakeholderAgent completed")
                    
    except Exception as e:
        logger.error(f"❌ Error in Phase 2: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": f"StakeholderAgent failed: {str(e)}"}
    
    # Check for citations in the content
    import re
    citation_tags = re.findall(r'\[\[Src:(\d+)\]\]', result["content"])
    result["citation_count"] = len(citation_tags)
    
    logger.info(f"📊 Analysis complete: {result['citation_count']} citations found")
    logger.info("=" * 60)
    
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
