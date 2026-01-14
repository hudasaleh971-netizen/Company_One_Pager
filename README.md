# Company Analysis Workflow

This project implements an agentic workflow using the Google Agent Developer Kit (ADK) to analyze company information from various sources. The workflow extracts key details (leadership, metrics, etc.) and compiles them into a structured Markdown report.

## Features

*   **Modular Code Structure:** The project is organized into a clear structure, separating agents, tools, and callbacks.
*   **Web Server for Debugging:** Uses the built-in ADK web server for easy testing and debugging of the agent workflow.
*   **Annual Report Processing:** Automatically finds and processes company annual reports (PDFs) for semantic search.
*   **Parallel Information Extraction:** Utilizes specialized AI agents to extract specific details in parallel.
*   **Iterative Refinement:** Employs a `LoopAgent` to review and refine the report until it is complete.

## Project Structure

```
.
├── app/
│   ├── agents/
│   │   ├── initial_search.py   # Agent to find the annual report
│   │   ├── extraction.py       # Parallel agents for data extraction
│   │   ├── refinement.py       # Loop for critiquing and refining the report
│   │   └── main_workflow.py    # Assembles the final sequential workflow
│   ├── tools.py              # Custom tools for agents
│   ├── callbacks.py          # Callback functions for agent hooks
│   └── state.py              # Defines the shared AppState class
├── main.py                   # Entry point for running with InMemoryRunner (for production)
├── server.py                 # Entry point for running the ADK web server (for testing)
├── requirements.txt          # Project dependencies
├── README.md                 # This file
└── .env                      # For storing the API key
```

## Setup and Installation

### 1. Create a Virtual Environment

```bash
# Using uv (recommended)
uv venv --python 3.11

# Or using Python's built-in venv
python -m venv .venv
```

### 2. Activate the Virtual Environment

**On Windows:**
```bash
.venv\Scripts\activate
```

**On macOS/Linux:**
```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Your Gemini API Key

Create a `.env` file in the root of the project and add your API key:

**.env file:**
```
GEMINI_API_KEY="YOUR_API_KEY"
```
**Replace `YOUR_API_KEY` with your actual Gemini API Key.**

## Testing with ADK Web Server

The ADK web server provides a robust way to test and debug the agentic workflow interactively.

### 1. Start the Server

Run the API server using uvicorn:

```bash
uvicorn app.api:app --reload
```
*   `--reload` will automatically restart the server when you make code changes.

The server will be available at `http://127.0.0.1:8000`.

### 2. Interact with the Workflow

You can interact with the agent using `curl` or any API client.

#### Example: Starting a new session

Use the following `curl` command to start a new analysis session. This example looks for information on "Etisalat (eand)" without providing a local report file.

```bash
curl -X POST http://127.0.0.1:8000/sessions/ \
-H "Content-Type: application/json" \
-d '{
  "request": {
    "text": "Analyze the company"
  },
  "context": {
    "company_name": "Etisalat (eand)",
    "annual_report_filename": null
  }
}'
```

#### Example: Starting a session with a local file

If you have a local PDF file (e.g., `my_report.pdf`) in the project\'s root directory, use this command:

```bash
# Make sure "my_report.pdf" exists in the same folder where you are running the command.
curl -X POST http://127.0.0.1:8000/sessions/ \
-H "Content-Type: application/json" \
-d '{
  "request": {
    "text": "Analyze the company"
  },
  "context": {
    "company_name": "Etisalat (eand)",
    "annual_report_filename": "my_report.pdf"
  }
}'
```

The server will stream the agent\'s thoughts, tool calls, and final output in the response.

## Running the Final Application

Once you have finished testing and debugging, you can run the application directly using `main.py`, which uses the `InMemoryRunner`.

```bash
python main.py
```
This will run the entire workflow in your terminal without the web interface.