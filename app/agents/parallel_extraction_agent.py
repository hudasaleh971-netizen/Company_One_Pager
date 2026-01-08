"""
Parallel Extraction Agent Factories

Provides factory functions to create fresh agent instances for extraction.
Each call returns a new agent instance to avoid parent agent conflicts.
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from pydantic import BaseModel, Field
from typing import Dict, Any
from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from app.models.citation import FinalResponse
from app.tools import ask_annual_report
from app.config import DEFAULT_RETRY_CONFIG

GEMINI_MODEL_NAME = "gemini-flash-latest"


# Output schema for agent responses



def _create_extraction_agent(name: str, task: str, output_key: str) -> LlmAgent:
    """
    Internal factory to create an extraction agent.
    
    Args:
        name: Name for the agent
        task: Task description for extraction
        output_key: Key to store output in session state
        
    Returns:
        A new LlmAgent configured for extraction
    """
    return LlmAgent(
        name=name,
        model=Gemini(model_name=GEMINI_MODEL_NAME, retry_options=DEFAULT_RETRY_CONFIG),
        tools=[FunctionTool(ask_annual_report)],
        output_schema=FinalResponse,
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


# ============================================================
# FACTORY FUNCTIONS - Use these to create fresh instances
# ============================================================

def create_leadership_agent(name: str = "LeadershipAgent") -> LlmAgent:
    """Create a fresh LeadershipAgent instance."""
    return _create_extraction_agent(
        name=name,
        task="List the current Management Team: Full name, role, education, and career summary.",
        output_key="leadership_data"
    )


def create_metrics_agent(name: str = "MetricsAgent") -> LlmAgent:
    """Create a fresh MetricsAgent instance."""
    return _create_extraction_agent(
        name=name,
        task="Collect key metrics: Borrowers, Employees, Loan outstanding, PAR > 30, Disbursals, Equity, Net income, Credit rating.",
        output_key="metrics_data"
    )


def create_stakeholder_agent(name: str = "StakeholderAgent") -> LlmAgent:
    """Create a fresh StakeholderAgent instance."""
    return _create_extraction_agent(
        name=name,
        task="List all known shareholders: Name, Ownership %, year and Notes.",
        output_key="stakeholder_data"
    )


def create_products_agent(name: str = "ProductsAgent") -> LlmAgent:
    """Create a fresh ProductsAgent instance."""
    return _create_extraction_agent(
        name=name,
        task="Extract a complete list of products and technologies with relevant statistics.",
        output_key="products_data"
    )


def create_overview_agent(name: str = "CompanyOverviewAgent") -> LlmAgent:
    """Create a fresh CompanyOverviewAgent instance."""
    return _create_extraction_agent(
        name=name,
        task="Generate 10-15 bullet points for a company background narrative (Founding, HQ, Business Model, etc.).",
        output_key="overview_data"
    )


def create_parallel_extraction_agent(name: str = "ParallelExtractionAgent") -> ParallelAgent:
    """Create a fresh ParallelExtractionAgent with all sub-agents."""
    return ParallelAgent(
        name=name,
        sub_agents=[
            create_leadership_agent(),
            create_metrics_agent(),
            create_stakeholder_agent(),
            create_products_agent(),
            create_overview_agent()
        ]
    )


# ============================================================
# BACKWARDS COMPATIBILITY - Default instances
# WARNING: Only use if not sharing across multiple workflows
# ============================================================

leadership_agent = create_leadership_agent()
metrics_agent = create_metrics_agent()
stakeholder_agent = create_stakeholder_agent()
products_agent = create_products_agent()
overview_agent = create_overview_agent()

parallel_extraction_agent = ParallelAgent(
    name="ParallelExtractionAgent",
    sub_agents=[leadership_agent, metrics_agent, stakeholder_agent, products_agent, overview_agent]
)
