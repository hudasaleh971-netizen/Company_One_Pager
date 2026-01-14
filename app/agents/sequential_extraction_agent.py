"""
Sequential Extraction Agent
============================
Runs extraction agents ONE AT A TIME to avoid rate limiting.
Uses SequentialAgent instead of ParallelAgent.
Uses Groq (via LiteLlm) for fast LLM inference.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool
from loguru import logger

from app.tools import ask_annual_report

# Groq configuration
# Model name uses groq/ prefix for LiteLlm
# API key is read from GROQ_API_KEY environment variable
GROQ_MODEL = "groq/llama-3.3-70b-versatile"

logger.info(f"📋 Sequential agents using Groq model: {GROQ_MODEL}")


def _create_agent(name: str, task: str, output_key: str) -> LlmAgent:
    """Create a single extraction agent using Groq via LiteLlm."""
    return LlmAgent(
        name=name,
        model=LiteLlm(model=GROQ_MODEL),
        tools=[FunctionTool(ask_annual_report)],
        # NOTE: Removed output_schema to avoid markdown-wrapped JSON validation errors
        instruction=f"""
        You are a specialized analyst for {{company_name}}.
        Use `ask_annual_report(store_name, question)` to extract information.
        
        CRITICAL: Always use store name: {{vector_store_name}}
        
        Your task: {task}
        
        Return the EXACT tool output JSON with cited_text and sources.
        """,
        output_key=output_key,
    )


def create_sequential_extraction_agent() -> SequentialAgent:
    """Create a SequentialAgent that runs all 5 extractors one at a time."""
    return SequentialAgent(
        name="SequentialExtractionAgent",
        sub_agents=[
            # _create_agent("LeadershipAgent", 
            #     "List the Management Team: name, role, education, career summary.", 
            #     "leadership_data"),
            # _create_agent("MetricsAgent", 
            #     "Collect key metrics: Borrowers, Employees, Loan outstanding, PAR>30, Disbursals, Equity, Net income.", 
            #     "metrics_data"),
            _create_agent("StakeholderAgent", 
                "List all shareholders with ownership percentage.", 
                "stakeholder_data"),
            # _create_agent("ProductsAgent", 
            #     "Extract list of products and technologies.", 
            #     "products_data"),
            # _create_agent("OverviewAgent", 
            #     "Generate 10-15 bullet points for company background.", 
            #     "overview_data"),
        ]
    )
