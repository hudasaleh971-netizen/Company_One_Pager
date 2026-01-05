import sys
import os

# Add project root to sys.path to allow imports from 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from google.adk.agents import LlmAgent, LoopAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool, google_search

from app.tools import exit_loop
from app.config import GEMINI_MODEL_NAME, DEFAULT_RETRY_CONFIG, MAX_REFINEMENT_ITERATIONS

critique_agent = LlmAgent(
    name="CritiqueAgent",
    model=Gemini(model_name=GEMINI_MODEL_NAME, retry_options=DEFAULT_RETRY_CONFIG),
    tools=[FunctionTool(exit_loop)],
    instruction="""
    You are a meticulous editor. Review the report.
    - If all sections have been adequately filled or noted as unavailable, you MUST call the `exit_loop` tool.
    - Otherwise, provide a concise list of the gaps to be filled.
    Report: {compiled_report}
    """,
    output_key="gaps"
)

refinement_agent = LlmAgent(
    name="RefinementAgent",
    model=Gemini(model_name=GEMINI_MODEL_NAME, retry_options=DEFAULT_RETRY_CONFIG),
    tools=[google_search],
    instruction="""
    You are a research assistant. Your task is to fill the gaps in the report by searching the web.
    Gaps: {gaps}
    Report: {compiled_report}
    Use your tools to find the missing information and provide an updated, complete report.
    """,
    output_key="compiled_report"
)

refinement_loop = LoopAgent(
    name="RefinementLoop",
    sub_agents=[critique_agent, refinement_agent],
    max_iterations=MAX_REFINEMENT_ITERATIONS,
)
