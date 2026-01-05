# Google ADK Web & Testing Guide

## 1. Using ADK Web (`google.adk.web`)

### Prerequisites
Ensure you have the dependencies installed:
```bash
pip install -r requirements.txt
```

### Launching the Web UI
Open your terminal in the project root (`c:\Users\HudaGoian\Documents\me\investment_Report`) and run:

```bash
adk web app/agents
```

This command will:
1.  Scan the `app/agents` directory.
2.  Discover all defined agents in the newly renamed files:
    -   `app/agents/initial_search_agent.py`
    -   `app/agents/parallel_extraction_agent.py`
    -   `app/agents/refinement_loop.py`
    -   `app/agents/company_analysis_workflow.py`
3.  Start a local server at `http://127.0.0.1:8000`.

### Interacting with the Agents
1.  Open `http://localhost:8000` in your browser.
2.  Select **CompanyAnalysisWorkflow** (or any specific agent you want to test) from the dropdown.
3.  In the chat interface, provide the input variables. This workflow expects `company_name`.
    *   Example Input: `Analyze Alphabet Inc.`
    *   *Note*: The ADK Web UI might ask for JSON input or allow you to set state variables. Ensure `company_name` is set.

## 2. Updated Code Structure

- **Agents**: Defined as top-level variables and renamed files:
    - `initial_search_agent.py` -> `initial_search_agent`
    - `parallel_extraction_agent.py` -> `parallel_extraction_agent`
    - `refinement_loop.py` -> `refinement_loop`
    - `company_analysis_workflow.py` -> `company_analysis_workflow`
- **Tools**: Synchronous tools in `app/tools.py`.
- **Callbacks**: Synchronous callbacks in `app/callbacks.py`.
- **Config**: Settings in `app/config.py`.

The system is now fully compatible with ADK Web auto-discovery.
