"""
Initial Search Agent Factory

Provides a factory function to create fresh InitialSearchAgent instances.
Each call returns a new agent instance to avoid parent agent conflicts.
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import google_search

from app.callbacks import process_and_prepare_file_callback
from app.config import GEMINI_MODEL_NAME, DEFAULT_RETRY_CONFIG


def create_initial_search_agent(name: str = "InitialSearchAgent") -> LlmAgent:
    """
    Factory function to create a fresh InitialSearchAgent instance.
    
    Args:
        name: Name for the agent (default: "InitialSearchAgent")
        
    Returns:
        A new LlmAgent instance configured for initial search
    """
    return LlmAgent(
        name=name,
        model=Gemini(model_name="gemini-2.5-flash", retry_options=DEFAULT_RETRY_CONFIG),
        tools=[google_search],
        instruction="""
        You are a financial researcher. Your goal is to provide the annual report source for {company_name}.
        
        *** CRITICAL: CHECK FILE PATH FIRST ***
        
        STEP 1 - CHECK IF FILE IS PROVIDED:
        Look at the value of {annual_report_filename}.
        - If it contains a file path (NOT "None" or empty), IMMEDIATELY return it as type "file".
        - DO NOT search the web if a file path is provided.
        
        STEP 2 - ONLY SEARCH IF NO FILE PROVIDED:
        If {annual_report_filename} is "None" or empty:
        - Search for: "{company_name} annual report 2024 filetype:pdf"
        - If 2024 not found, try 2023
        - Look for DIRECT .pdf URLs (ending in .pdf)
        - DO NOT use URLs containing "grounding-api-redirect" - these are not valid PDFs
        
        OUTPUT JSON ONLY:
        
        If file path is provided:
        ```json
        {"status": "FOUND", "type": "file", "details": "{annual_report_filename}", "company": "{company_name}"}
        ```
        
        If PDF URL found via search:
        ```json
        {"status": "FOUND", "type": "url", "details": "THE_DIRECT_PDF_URL", "company": "{company_name}"}
        ```
        
        If nothing found:
        ```json
        {"status": "NOT_FOUND", "type": "", "details": "", "company": "{company_name}"}
        ```
        """,
        output_key="initial_search_output",
        after_agent_callback=process_and_prepare_file_callback
    )


# For backwards compatibility - create a default instance
# WARNING: Only use this if you're not using it in multiple workflows
initial_search_agent = create_initial_search_agent()
