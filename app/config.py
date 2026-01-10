import os
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

# --- Gemini Configuration ---
GEMINI_MODEL_NAME = "gemini-2.5-flash"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- Retry Configuration ---
DEFAULT_RETRY_CONFIG = types.HttpRetryOptions(
    attempts=5, 
    exp_base=10, 
    initial_delay=5, 
    http_status_codes=[429, 500, 503, 504]
)

# --- Agent Configurations ---
MAX_REFINEMENT_ITERATIONS = 2
