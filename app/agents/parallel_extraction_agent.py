import sys
import os

# Add project root to sys.path to allow imports from 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool

from app.tools import ask_annual_report
from app.config import DEFAULT_RETRY_CONFIG
GEMINI_MODEL_NAME = "gemini-flash-latest"
def _create_agent(name: str, task: str, output_key: str):
    return LlmAgent(
        name=name,
        model=Gemini(model_name=GEMINI_MODEL_NAME, retry_options=DEFAULT_RETRY_CONFIG),
        tools=[FunctionTool(ask_annual_report)],
        instruction=f"""
        You are a specialized analyst for {{company_name}}.
        You have a tool `ask_annual_report(store_name, question)` to ask questions to the company's annual report.
        
        CRITICAL: Always use the store name provided here: {{vector_store_name}}.
        Pass this EXACT value as the `store_name` argument to the tool.

        If the tool returns an error, state that the information could not be retrieved.
        
        Your task is to extract the following information:
        {task}
        
        Provide a detailed and structured output based on the information from the annual report.
        """,
        output_key=output_key,
    )

leadership_agent = _create_agent("LeadershipAgent", "List the current Management Team: Full name, role, education, and career summary.", "leadership_data")
metrics_agent = _create_agent("MetricsAgent", "Collect key metrics: Borrowers, Employees, Loan outstanding, PAR > 30, Disbursals, Equity, Net income, Credit rating.", "metrics_data")
stakeholder_agent = _create_agent("StakeholderAgent", "List all known shareholders: Name, Ownership %, and Notes.", "stakeholder_data")
products_agent = _create_agent("ProductsAgent", "Extract a complete list of products and technologies with relevant statistics.", "products_data")
overview_agent = _create_agent("CompanyOverviewAgent", "Generate 10-15 bullet points for a company background narrative (Founding, HQ, Business Model, etc.).", "overview_data")

parallel_extraction_agent = ParallelAgent(
    name="ParallelExtractionAgent",
    sub_agents=[leadership_agent, metrics_agent, stakeholder_agent, products_agent, overview_agent]
)
