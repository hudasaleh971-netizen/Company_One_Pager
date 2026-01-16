"""
PPT Company Analysis Workflow
==============================
New workflow that uses SequentialExtractionAgent and outputs SlideData JSON
for PPT generation. Includes after_agent_callback to generate slides on completion.
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from google.adk.agents import SequentialAgent, LoopAgent, LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool

from app.agents.initial_search_agent import create_initial_search_agent
from app.agents.sequential_extraction_agent import create_sequential_extraction_agent
from app.tools import exit_loop
from app.ppt_generator import generate_ppt_callback
from app.models.ppt_models import SlideData
from app.config import GEMINI_MODEL_NAME, DEFAULT_RETRY_CONFIG, MAX_REFINEMENT_ITERATIONS


def create_ppt_report_compilation_agent(name: str = "PPTReportCompilationAgent") -> LlmAgent:
    """
    Create a ReportCompilationAgent that outputs SlideData JSON for PPT generation.
    
    This agent takes the extracted data and compiles it into the SlideData format
    matching Template.pptx placeholders.
    """
    return LlmAgent(
        name=name,
        model=Gemini(model_name=GEMINI_MODEL_NAME, retry_options=DEFAULT_RETRY_CONFIG),
        output_schema=SlideData,
        instruction="""
        You are a senior analyst. Compile the extracted data into a structured JSON for PowerPoint slide generation.
        
        Use the following extracted data for {company_name}:
        
        Company Overview: {overview_data}
        Products: {products_data}
        Leadership: {leadership_data}
        Metrics: {metrics_data}
        Stakeholders: {stakeholder_data}
        
        OUTPUT REQUIREMENTS:
        You MUST output a JSON object with these exact fields:
        
        1. COMPANY_NAME: The company name
        2. COUNTRY: The country/region where the company operates
        3. BACKGROUND_SUMMARY: Bullet points about the company (use • for bullets, separated by newlines)
        4. KEY_PRODUCTS: Description of products and services
        5. Unit: The unit for financial metrics (default "USDm")
        6. year: The year for statistics (default "2025")
        7. BORROWERS_VALUE: Number of borrowers/customers
        8. EMPLOYEES_VALUE: Number of employees
        9. OUTSTANDING_VALUE: Loan outstanding amount
        10. PAR_VALUE: PAR > 30 value (use "n/d" if not available)
        11. DISBURSALS_VALUE: Total disbursals
        12. EQUITY_VALUE: Equity amount (use "n/d" if not available)
        13. NET_INCOME_VALUE: Net income (use "n/d" if not available)
        14. CREDIT_RATING_VALUE: Credit rating (use "n/d" if not available)
        15. TABLE_MANAGEMENT: List of management team members, each with:
            - name: Full name
            - position: Job title
            - bio: Career summary
        16. TABLE_SHAREHOLDERS: List of shareholders, each with:
            - name: Shareholder name
            - ownership_percentage: Ownership % or "n/d"
        
        For any metric not found in the data, use "n/d" (not disclosed).
        """,
        output_key="slide_data"
    )


def create_ppt_critique_agent(name: str = "PPTCritiqueAgent") -> LlmAgent:
    """CritiqueAgent that reviews SlideData JSON for completeness."""
    return LlmAgent(
        name=name,
        model=Gemini(model_name=GEMINI_MODEL_NAME, retry_options=DEFAULT_RETRY_CONFIG),
        tools=[FunctionTool(exit_loop)],
        instruction="""
        You are a meticulous editor reviewing the slide data JSON.
        
        Check if the following fields have been adequately filled:
        - COMPANY_NAME and COUNTRY are present
        - BACKGROUND_SUMMARY has at least 3 bullet points
        - KEY_PRODUCTS is not empty
        - At least some financial metrics are filled (not all "n/d")
        - TABLE_MANAGEMENT has at least 1 entry
        - TABLE_SHAREHOLDERS has at least 1 entry OR is marked as not disclosed
        
        Slide Data: {slide_data}
        
        If the data is adequate for a professional one-pager, call the `exit_loop` tool.
        Otherwise, provide a concise list of gaps to be filled.
        """,
        output_key="gaps"
    )


def create_ppt_refinement_agent(name: str = "PPTRefinementAgent") -> LlmAgent:
    """RefinementAgent that fills gaps in SlideData."""
    from google.adk.tools import google_search
    
    return LlmAgent(
        name=name,
        model=Gemini(model_name=GEMINI_MODEL_NAME, retry_options=DEFAULT_RETRY_CONFIG),
        tools=[google_search],
        output_schema=SlideData,
        instruction="""
        You are a research assistant. Fill the gaps in the slide data by searching the web.
        
        Gaps identified: {gaps}
        Current Slide Data: {slide_data}
        
        Use web search to find the missing information. 
        Output the complete, updated SlideData JSON with all fields filled.
        Use "n/d" for any information that truly cannot be found.
        """,
        output_key="slide_data"
    )


def create_ppt_refinement_loop(name: str = "PPTRefinementLoop") -> LoopAgent:
    """
    Create a LoopAgent for refining SlideData.
    Includes after_agent_callback to generate PPT when loop exits.
    """
    return LoopAgent(
        name=name,
        sub_agents=[
            create_ppt_critique_agent(),
            create_ppt_refinement_agent()
        ],
        max_iterations=MAX_REFINEMENT_ITERATIONS,
        after_agent_callback=generate_ppt_callback,  # Generate PPT when loop exits
    )


def create_ppt_workflow(name: str = "PPTCompanyAnalysisWorkflow") -> SequentialAgent:
    """
    Create the complete PPT Company Analysis Workflow.
    
    Pipeline:
    1. InitialSearchAgent - Find/upload annual report to vector store
    2. SequentialExtractionAgent - Extract data one section at a time
    3. PPTReportCompilationAgent - Compile data into SlideData JSON
    4. PPTRefinementLoop - Refine data and generate PPT on exit
    """
    return SequentialAgent(
        name=name,
        sub_agents=[
            create_initial_search_agent(),
            create_sequential_extraction_agent(),
            create_ppt_report_compilation_agent(),
            create_ppt_refinement_loop(),
        ],
    )


# Factory function for API use
def get_ppt_workflow() -> SequentialAgent:
    """Get a fresh instance of the PPT workflow."""
    return create_ppt_workflow()
