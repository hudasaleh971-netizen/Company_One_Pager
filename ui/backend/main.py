"""
FastAPI Backend for Citation UI

Provides API endpoints for running citation agents.
"""

import os
import sys
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger
import shutil
import uuid

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from ui.backend.agent_runner import run_analysis

# Configure loguru
logger.add("logs/api.log", rotation="10 MB", level="DEBUG")

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

# Upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class AnalysisRequest(BaseModel):
    company_name: str
    file_path: Optional[str] = None


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
    logger.info(f"📥 Received analysis request for: {company_name}")
    
    file_path = None
    
    # Handle file upload
    if file:
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            logger.info(f"📁 Saved uploaded file: {file_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save file: {e}")
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")
    
    # Run analysis
    try:
        result = await run_analysis(company_name, file_path)
        
        if "error" in result:
            return AnalysisResponse(
                company_name=company_name,
                content="",
                sources={},
                has_citations=False,
                citation_count=0,
                error=result["error"]
            )
        
        return AnalysisResponse(
            company_name=result.get("company_name", company_name),
            content=result.get("content", ""),
            sources=result.get("sources", {}),
            has_citations=result.get("has_citations", False),
            citation_count=result.get("citation_count", 0)
        )
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
