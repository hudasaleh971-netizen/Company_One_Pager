import os
import re
import time
import json
import requests
from google import genai
from google.genai import types

# Gemini Developer API client for file store operations
# File Search Store APIs are ONLY available in the Gemini Developer client, NOT Vertex AI
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


def process_and_prepare_file_callback(callback_context):
    """
    Parses the output of the InitialSearchAgent, downloads the file if a URL is found,
    and then uploads the file to a Gemini File Search Store (vector store).
    
    NOTE: Uses Gemini Developer API (not Vertex AI) for file store operations.
    """
    print("\n--- [Callback] Processing Search Results & Preparing File ---")
    state = callback_context.state
    raw_output = state.get("initial_search_output", "")
    company_name = state.get("company_name", "UnknownCompany")
    
    file_path = None
    
    try:
        json_match = re.search(r'```json\s*(.*?)\s*```', raw_output, re.DOTALL)
        clean_json_str = json_match.group(1) if json_match else raw_output.strip()
        data = json.loads(clean_json_str)
        
        status = data.get("status")
        if status != "FOUND":
            print("⏭️ Status is NOT_FOUND. No file to process.")
            state["vector_store_name"] = None
            return

        source_type = data.get("type")
        details = data.get("details")
        print(f"✅ Parsed JSON successfully. Status: FOUND, Type: {source_type}.")

        if source_type == "file":
            # File path provided directly - use it
            file_path = details
            print(f"📂 Using provided file path: {file_path}")
            
        elif source_type == "url":
            raw_url = details
            print(f"🔍 Checking URL: {raw_url}")
            
            # Skip invalid grounding redirect URLs
            if "grounding-api-redirect" in raw_url:
                print("❌ Skipping grounding redirect URL - not a direct PDF link.")
                print("⚠️ Please provide a direct PDF file path or URL.")
                state["vector_store_name"] = None
                return

            try:
                headers = {'User-Agent': 'Gemini ADK Agent sample@example.com'}
                
                # Try to download with SSL verification first, fallback to no-verify
                try:
                    response = requests.get(raw_url, headers=headers, allow_redirects=True, stream=True, timeout=30)
                except requests.exceptions.SSLError:
                    print("⚠️ SSL error, retrying without verification...")
                    response = requests.get(raw_url, headers=headers, allow_redirects=True, stream=True, timeout=30, verify=False)
                
                final_url = response.url
                content_type = response.headers.get('Content-Type', '').lower()
                
                is_pdf_content = 'application/pdf' in content_type
                is_pdf_extension = final_url.lower().endswith('.pdf')
                
                if not (is_pdf_content or is_pdf_extension):
                    print(f"❌ Error: URL is not a PDF (Content-Type: {content_type})")
                    print(f"   Resolved URL: {final_url}")
                    state["vector_store_name"] = None
                    return
                
                print(f"📂 Downloading PDF from: {final_url}")
                
                file_path = f"{company_name}_annual_report.pdf"
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192): 
                        f.write(chunk)
                        
                print(f"✅ File downloaded: {file_path}")

            except requests.exceptions.RequestException as e:
                print(f"❌ Failed to download file: {e}")
                state["vector_store_name"] = None
                return

    except (json.JSONDecodeError, AttributeError) as e:
        print(f"❌ Error parsing JSON from agent output: {e}")
        state["vector_store_name"] = None
        return

    # Upload to vector store
    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            print("❌ Error: File is empty.")
            state["vector_store_name"] = None
            return

        print(f"🚀 Uploading '{file_path}' ({file_size} bytes) to Gemini...")
        try:
            # Use Gemini Developer API client (NOT Vertex AI) for file store operations
            # File Search Store APIs are only available in the Gemini Developer client
            # IMPORTANT: vertexai=False is required to override GOOGLE_GENAI_USE_VERTEXAI env var
            gemini_client = genai.Client(api_key=GEMINI_API_KEY, vertexai=False)
            
            print("   Creating File Search Store...")
            file_search_store = gemini_client.file_search_stores.create(
                config=types.CreateFileSearchStoreConfig(display_name=f'{company_name} Store')
            )
            print(f"   Store created: {file_search_store.name}")
            
            print("   Uploading file...")
            upload_op = gemini_client.file_search_stores.upload_to_file_search_store(
                file_search_store_name=file_search_store.name,
                file=file_path,
                config=types.UploadToFileSearchStoreConfig(display_name='Annual Report PDF')
            )
            
            print("   Processing", end="")
            while not (upload_op := gemini_client.operations.get(upload_op)).done:
                time.sleep(5)
                print(".", end="")
            
            state["vector_store_name"] = file_search_store.name
            print(f"\n✅ Vector Store Ready: {file_search_store.name}")

        except Exception as e:
            print(f"❌ Error uploading: {e}")
            state["vector_store_name"] = None
    else:
        print(f"❌ File not found: {file_path}")
        state["vector_store_name"] = None
