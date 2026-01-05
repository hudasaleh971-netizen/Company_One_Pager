import time
from google.genai import types, client

from app.config import GEMINI_API_KEY, GEMINI_MODEL_NAME

def ask_annual_report(store_name: str, question: str) -> str:
    """
    Queries the currently loaded Annual Report PDF from the vector store.
    """
    if not store_name:
        return "Error: No Annual Report vector store has been created or is available."

    print(f"🔎 [Tool] Querying Store '{store_name}': {question[:80]}...")
    time.sleep(2)  # To avoid rate limiting issues

    try:
        gemini_client = client.Client(api_key=GEMINI_API_KEY)
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=question,
            config=types.GenerateContentConfig(
                tools=[types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store_name]
                    )
                )],
            )
        )
        return response.text
    except Exception as e:
        print(f"Tool Error: {e}")
        return f"Tool Error: {str(e)}"

def exit_loop(callback_context):
    """
    A tool that the CritiqueAgent can call to signal that the report is approved
    and the refinement loop should be terminated.
    """
    print("✅ [Tool] Report approved. Exiting refinement loop.")
    return "Report approved. Exiting loop."
