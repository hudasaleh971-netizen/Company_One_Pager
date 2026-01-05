import sys
import os

# Add project root to sys.path to allow imports from 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.models.google_llm import Gemini

from app.agents.initial_search_agent import initial_search_agent
from app.agents.parallel_extraction_agent import parallel_extraction_agent
from app.agents.refinement_loop import refinement_loop
from app.config import GEMINI_MODEL_NAME, DEFAULT_RETRY_CONFIG

report_compilation_agent = LlmAgent(
    name="ReportCompilationAgent",
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

company_analysis_workflow = SequentialAgent(
    name="CompanyAnalysisWorkflow",
    sub_agents=[
        initial_search_agent,
        parallel_extraction_agent,
        report_compilation_agent,
        refinement_loop,
    ],
)

