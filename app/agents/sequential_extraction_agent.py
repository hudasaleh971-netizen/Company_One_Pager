"""
Sequential Extraction Agent
============================
Runs extraction agents ONE AT A TIME to avoid rate limiting.
Uses SequentialAgent instead of ParallelAgent.
Uses Gemini 2.5 Flash Lite for fast LLM inference.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from loguru import logger

from app.tools import ask_annual_report
from app.models.citation import FinalResponse
from app.config import DEFAULT_RETRY_CONFIG

# Gemini configuration
# Use stable model available on Vertex AI (not preview versions)
GEMINI_MODEL = "gemini-2.5-flash-lite"

logger.info(f"📋 Sequential agents using Gemini model: {GEMINI_MODEL}")


def _create_agent(name: str, task: str, output_key: str) -> LlmAgent:
    """Create a single extraction agent with proper structured output."""
    logger.debug(f"🔧 Creating sequential extraction agent: {name} -> output_key={output_key}")
    return LlmAgent(
        name=name,
        model=Gemini(model_name=GEMINI_MODEL, retry_options=DEFAULT_RETRY_CONFIG),
        tools=[FunctionTool(ask_annual_report)],
        output_schema=FinalResponse,  # Enforce structured output
        instruction=f"""
        You are a specialized analyst for {{company_name}}.
        You have a tool `ask_annual_report(store_name, question)` to extract information from the company's annual report.
        
        CRITICAL: Always use the store name: {{vector_store_name}}
        Pass this EXACT value as the `store_name` argument.

        Your task:
        {task}
        
        *** CRITICAL: OUTPUT FORMAT ***
        
        The tool returns JSON with:
        - "cited_text": Text with [[Src:XXX]] citation tags
        - "sources": Dictionary of source documents with page numbers and text
        
        You MUST return the EXACT tool output as-is (as JSON).
        DO NOT summarize or modify it. The sources dictionary is required for interactive citations.
        
        Example correct output:
        {{"cited_text": "Revenue grew 15%[[Src:101]]...", "sources": {{"src_101": {{"title": "...", "page_number": "Page 5", "raw_text": "..."}}}}}}
        """,
        output_key=output_key,
    )


def create_sequential_extraction_agent() -> SequentialAgent:
    """Create a SequentialAgent that runs all 5 extractors one at a time."""
    return SequentialAgent(
        name="SequentialExtractionAgent",
        sub_agents=[
            _create_agent("LeadershipAgent", 
                "List the Management Team: name, role, education, career summary.", 
                "leadership_data"),
            _create_agent("MetricsAgent", 
                "Collect key metrics: Borrowers, Employees, Loan outstanding, PAR>30, Disbursals, Equity, Net income.", 
                "metrics_data"),
            _create_agent("StakeholderAgent", 
                "List all shareholders with ownership percentage.", 
                "stakeholder_data"),
            _create_agent("ProductsAgent", 
                "Extract list of products and technologies.", 
                "products_data"),
            _create_agent("OverviewAgent", 
                "Generate 10-15 bullet points for company background.", 
                "overview_data"),
        ]
    )
