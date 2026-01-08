"""
Company Analysis Workflow

Uses factory functions to create fresh agent instances.
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.models.google_llm import Gemini

from app.agents.initial_search_agent import create_initial_search_agent
from app.agents.parallel_extraction_agent import create_parallel_extraction_agent
from app.agents.refinement_loop import refinement_loop
from app.config import GEMINI_MODEL_NAME, DEFAULT_RETRY_CONFIG


def create_report_compilation_agent(name: str = "ReportCompilationAgent") -> LlmAgent:
    """Create a fresh ReportCompilationAgent instance."""
    return LlmAgent(
        name=name,
        model=Gemini(model_name=GEMINI_MODEL_NAME, retry_options=DEFAULT_RETRY_CONFIG),
        instruction="""
        You are a senior analyst. Compile the extracted data into a single, cohesive, and well-structured Markdown report for {company_name}.
        Format the output cleanly with clear headings for each section. If a section has no data, state that the information was not available.
        
        Company Overview Data: {overview_data}
        Products Data: {products_data}
        Leadership Data: {leadership_data}
        Metrics Data: {metrics_data}
        Stakeholder Data: {stakeholder_data}
        """,
        output_key="compiled_report"
    )


def create_company_analysis_workflow(name: str = "CompanyAnalysisWorkflow") -> SequentialAgent:
    """
    Factory function to create a fresh CompanyAnalysisWorkflow.
    
    Creates fresh instances of all sub-agents to avoid parent conflicts.
    """
    return SequentialAgent(
        name=name,
        sub_agents=[
            create_initial_search_agent(),
            create_parallel_extraction_agent(),
            create_report_compilation_agent(),
            refinement_loop,
        ],
    )


# For backwards compatibility - create a default instance
# WARNING: Only use if not sharing across multiple places
company_analysis_workflow = create_company_analysis_workflow()
