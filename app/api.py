"""
FastAPI Backend for Citation UI

Uses factory functions to create fresh SequentialAgent instances.
Returns FinalResponse structure with clean_text, cited_text, citations, sources.
"""

import os
import sys
import uuid
import re
import json
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from google.genai import types
from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Import factory functions (not instances)
from app.agents.initial_search_agent import create_initial_search_agent
from app.agents.parallel_extraction_agent import create_stakeholder_agent
from app.models.citation import FinalResponse, CitationMetadata, SourceDocument, extract_citations_from_tags

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
    LOG_DIR / "api_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

logger.info(f"📁 Logs: {LOG_DIR}")

# ============ UPLOAD DIRECTORY ============
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# ============ FASTAPI APP ============
app = FastAPI(
    title="Citation Analysis API",
    description="API for running company analysis with citation support",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ RESPONSE MODELS ============
class CitationItem(BaseModel):
    start_index: int
    end_index: int
    source_id: str


class SourceItem(BaseModel):
    source_id: str
    title: str
    page_number: str
    raw_text: str


class AnalysisResponse(BaseModel):
    company_name: str
    clean_text: str
    cited_text: str
    citations: List[CitationItem]
    sources: Dict[str, SourceItem]
    error: Optional[str] = None


def create_citation_sequential_agent() -> SequentialAgent:
    """Factory to create a fresh SequentialAgent for each request."""
    return SequentialAgent(
        name="APICitationAgent",
        sub_agents=[
            create_initial_search_agent("APIInitialSearchAgent"),
            create_stakeholder_agent("APIStakeholderAgent"),
        ],
    )


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
    """Analyze a company from its annual report."""
    logger.info("=" * 60)
    logger.info(f"📥 Analysis request: {company_name}")
    
    file_path = None
    
    # Handle file upload
    if file:
        file_ext = os.path.splitext(file.filename)[1] or ".pdf"
        unique_filename = f"{company_name.replace(' ', '_')}_{uuid.uuid4().hex[:8]}{file_ext}"
        file_path = str(UPLOAD_DIR / unique_filename)
        
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            logger.info(f"📁 Saved: {file_path} ({os.path.getsize(file_path)} bytes)")
        except Exception as e:
            logger.error(f"❌ File save failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    
    # Run analysis
    try:
        result = await run_sequential_agent(company_name, file_path)
        
        if result.get("error"):
            return AnalysisResponse(
                company_name=company_name,
                clean_text="",
                cited_text="",
                citations=[],
                sources={},
                error=result["error"]
            )
        
        return AnalysisResponse(
            company_name=company_name,
            clean_text=result.get("clean_text", ""),
            cited_text=result.get("cited_text", ""),
            citations=result.get("citations", []),
            sources=result.get("sources", {})
        )
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def run_sequential_agent(company_name: str, file_path: Optional[str] = None) -> dict:
    """Run the SequentialAgent and return FinalResponse structure."""
    logger.info(f"🚀 Running SequentialAgent for: {company_name}")
    
    APP_NAME = "citation_api"
    USER_ID = "api_user"
    SESSION_ID = f"session_{uuid.uuid4().hex[:8]}"
    
    session_service = InMemorySessionService()
    
    initial_state = {
        "company_name": company_name,
        "annual_report_filename": file_path if file_path else ""
    }
    
    logger.info(f"📝 Session: {initial_state}")
    
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state=initial_state
    )
    
    # Create fresh agent using factory
    citation_agent = create_citation_sequential_agent()
    
    runner = Runner(
        agent=citation_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    result = {
        "clean_text": "",
        "cited_text": "",
        "citations": [],
        "sources": {}
    }
    
    try:
        query = types.Content(
            role='user', 
            parts=[types.Part(text="Find the annual report and list all known shareholders with their ownership percentages.")]
        )
        
        events = runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=query)
        
        last_output = None
        last_author = None
        event_count = 0

        async for event in events:
            event_count += 1
            author = getattr(event, 'author', 'unknown')
            
            # Log all events for debugging
            logger.debug(f"📨 Event #{event_count} from: {author}, is_final: {event.is_final_response()}")
            
            if event.is_final_response():
                if event.content and event.content.parts:
                    raw_output = event.content.parts[0].text
                    logger.info(f"📝 Final response from {author}: {len(raw_output)} chars")
                    logger.debug(f"📝 First 200 chars: {raw_output[:200]}...")
                    
                    # Store each final response - we want the LAST one (StakeholderAgent)
                    last_output = raw_output
                    last_author = author
        
        logger.info(f"📊 Total events: {event_count}, Final author: {last_author}")
        
        # Retrieve FinalResponse from session state (stored by tools.py)
        # This bypasses agent text output which loses structured data
        session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
        final_response = session.state.get("final_response")
        
        if final_response:
            logger.info(f"✅ Retrieved FinalResponse from session state")
            
            cited_text = final_response.get("cited_text", "")
            sources_raw = final_response.get("sources", {})
            
            logger.info(f"📚 Found {len(sources_raw)} sources with metadata")
            
            # Use shared parser from citation.py
            clean_text, citations = extract_citations_from_tags(cited_text)
            
            # Convert CitationMetadata objects to dicts for response
            citations_dicts = [{
                "start_index": c.start_index,
                "end_index": c.end_index,
                "source_id": c.source_id
            } for c in citations]
            
            # Convert sources - preserve full metadata for tooltips
            sources = {}
            for src_id, src_data in sources_raw.items():
                if isinstance(src_data, dict):
                    sources[src_id] = {
                        "source_id": src_id,
                        "title": src_data.get("title", "Annual Report"),
                        "page_number": src_data.get("page_number", ""),
                        "raw_text": src_data.get("raw_text", "")
                    }
            
            result = {
                "clean_text": clean_text,
                "cited_text": cited_text,
                "citations": citations_dicts,
                "sources": sources
            }
            
            logger.info(f"✅ Final: {len(citations)} citations, {len(sources)} sources")
        else:
            logger.warning("⚠️ No FinalResponse in session state - using agent output")
            # Fallback to agent output if session state empty
            if last_output:
                cited_text = last_output
                clean_text, citations = extract_citations_from_tags(cited_text)
                citations_dicts = [{
                    "start_index": c.start_index,
                    "end_index": c.end_index,
                    "source_id": c.source_id
                } for c in citations]
                result = {
                    "clean_text": clean_text,
                    "cited_text": cited_text,
                    "citations": citations_dicts,
                    "sources": {}
                }
                     
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
        if not session.state.get("vector_store_name"):
            return {"error": "Failed to create vector store. Check file upload."}
        return {"error": str(e)}
    
    return result



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
