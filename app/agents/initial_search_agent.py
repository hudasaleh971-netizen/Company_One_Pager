import sys
import os

# Add project root to sys.path to allow imports from 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import google_search

from app.callbacks import process_and_prepare_file_callback
from app.config import GEMINI_MODEL_NAME, DEFAULT_RETRY_CONFIG

initial_search_agent = LlmAgent(
    name="InitialSearchAgent",
    model=Gemini(model_name=GEMINI_MODEL_NAME, retry_options=DEFAULT_RETRY_CONFIG),
    tools=[google_search],
    instruction="""
    You are a financial researcher. Your goal is to provide the annual report source for {{company_name}}.
    
    *** CRITICAL: CHECK FILE PATH FIRST ***
    
    STEP 1 - CHECK IF FILE IS PROVIDED:
    Look at the value of {{annual_report_filename}}.
    - If it contains a file path (NOT "None" or empty), IMMEDIATELY return it as type "file".
    - DO NOT search the web if a file path is provided.
    
    STEP 2 - ONLY SEARCH IF NO FILE PROVIDED:
    If {{annual_report_filename}} is "None" or empty:
    - Search for: "{{company_name}} annual report 2024 filetype:pdf"
    - If 2024 not found, try 2023
    - Look for DIRECT .pdf URLs (ending in .pdf)
    - DO NOT use URLs containing "grounding-api-redirect" - these are not valid PDFs
    
    OUTPUT JSON ONLY:
    
    If file path is provided:
    ```json
    {"status": "FOUND", "type": "file", "details": "{{annual_report_filename}}", "company": "{{company_name}}"}
    ```
    
    If PDF URL found via search:
    ```json
    {"status": "FOUND", "type": "url", "details": "THE_DIRECT_PDF_URL", "company": "{{company_name}}"}
    ```
    
    If nothing found:
    ```json
    {"status": "NOT_FOUND", "type": "", "details": "", "company": "{{company_name}}"}
    ```
    """,
    output_key="initial_search_output",
    after_agent_callback=process_and_prepare_file_callback
)
