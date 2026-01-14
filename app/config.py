import os
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

# --- Gemini Configuration ---
# Multi-model setup to distribute API load and avoid rate limiting
#
# Model Distribution Strategy:
#   1. TOOL_MODEL: Used for file_search queries in ask_annual_report tool
#   2. AGENT_MODELS: Alternating models for parallel extraction agents
#      - 5 parallel agents split across 2 models (3 + 2 distribution)
#
# Available stable models with high output tokens (65K):
#   - gemini-2.5-flash-lite: Stable, good for parallel tasks
#   - gemini-2.5-flash: More capable, stable
#   - gemini-2.0-flash: Fast, reliable
#   - gemini-2.0-flash-lite: Lightweight, different rate pool

# Model for tools (file search queries)
# NOTE: gemini-2.0-flash-lite quota exhausted on free tier, using gemini-2.5-flash instead
TOOL_MODEL_NAME = "gemini-2.5-flash"

# Models for parallel extraction agents (alternating to split load)
AGENT_MODEL_PRIMARY = "gemini-2.5-flash-lite"   # Agents 0, 2, 4
AGENT_MODEL_SECONDARY = "gemini-3.0-flash"      # Agents 1, 3

# Legacy single model (kept for backwards compatibility)
GEMINI_MODEL_NAME = AGENT_MODEL_PRIMARY
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- Groq Configuration ---
# Used by sequential_extraction_agent via LiteLlm
# Set GROQ_API_KEY in your .env file
# LiteLlm reads it automatically
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL_NAME = "groq/llama-3.3-70b-versatile"

# --- API Calls Per Full Execution ---
# Per analysis, the API makes approximately:
#   - InitialSearchAgent: ~1-3 calls
#   - ParallelExtractionAgent (5 sub-agents): ~2 calls each = ~10 calls
#   - Tool calls (ask_annual_report): 5 calls (one per section)
#   - Total: ~16-18 LLM API calls per full execution
#
# With 10 RPM limit, parallel agents WILL hit rate limits.
# The retry config handles 429 errors with exponential backoff.

# --- Retry Configuration ---
DEFAULT_RETRY_CONFIG = types.HttpRetryOptions(
    attempts=5, 
    exp_base=10, 
    initial_delay=5, 
    http_status_codes=[429, 500, 503, 504]
)

# --- Agent Configurations ---
MAX_REFINEMENT_ITERATIONS = 2
