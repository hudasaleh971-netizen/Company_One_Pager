import sys
import os

# Add project root to sys.path to allow imports from 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from pydantic import BaseModel, Field
from typing import Dict, Any, List
from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool

from app.tools import ask_annual_report
from app.config import DEFAULT_RETRY_CONFIG

GEMINI_MODEL_NAME = "gemini-flash-latest"


# Output schema for agent responses - includes cited_text from FinalResponse
class CitedContent(BaseModel):
    """Output schema that includes the cited content from the tool's FinalResponse."""
    content: str = Field(
        ..., 
        description="The extracted information with [[Src:XXX]] citation tags. Copy this directly from the 'cited_text' field of the tool output."
    )
    sources: Dict[str, Any] = Field(
        default_factory=dict,
        description="The sources dictionary from the tool output. Copy this directly from the 'sources' field."
    )


def _create_agent(name: str, task: str, output_key: str):
    return LlmAgent(
        name=name,
        model=Gemini(model_name=GEMINI_MODEL_NAME, retry_options=DEFAULT_RETRY_CONFIG),
        tools=[FunctionTool(ask_annual_report)],
        output_schema=CitedContent,
        instruction=f"""
        You are a specialized analyst for {{company_name}}.
        You have a tool `ask_annual_report(store_name, question)` to ask questions to the company's annual report.
        
        CRITICAL: Always use the store name provided here: {{vector_store_name}}.
        Pass this EXACT value as the `store_name` argument to the tool.

        If the tool returns an error, state that the information could not be retrieved.
        
        Your task is to extract the following information:
        {task}
        
        *** IMPORTANT: HANDLING THE TOOL OUTPUT ***
        
        The tool returns a FinalResponse dictionary with these fields:
        - "clean_text": Text WITHOUT citation tags
        - "cited_text": Text WITH [[Src:XXX]] citation tags embedded
        - "citations": List of citation metadata
        - "sources": Dictionary of source documents for tooltips
        
        YOU MUST:
        1. Use the "cited_text" field from the tool output for your response
        2. Copy the [[Src:XXX]] tags exactly as they appear
        3. Include the "sources" dictionary in your output
        
        Example tool output:
        {{
          "clean_text": "Revenue grew 20%.",
          "cited_text": "Revenue grew 20% [[Src:100]].",
          "citations": [...],
          "sources": {{"src_100": {{...}}}}
        }}
        
        Your response MUST be:
        {{
          "content": "Revenue grew 20% [[Src:100]].",
          "sources": {{"src_100": {{...}}}}
        }}
        
        DO NOT REMOVE [[Src:XXX]] TAGS. They are required for source attribution.
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
