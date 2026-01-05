from google.genai import client, types
from app.config import GEMINI_API_KEY

def force_cleanup():
    print("🧹 Starting Cleanup...")
    gemini_client = client.Client(api_key=GEMINI_API_KEY)

    # --- STEP 1: DELETE STANDALONE FILES ---
    print("\n--- Step 1: Deleting Standalone Files ---")
    try:
        files = list(gemini_client.files.list())
        print(f"Found {len(files)} standalone files.")
        for f in files:
            try:
                gemini_client.files.delete(name=f.name)
                print(f"   ✅ Deleted file: {f.name}")
            except Exception as e:
                print(f"   ❌ Failed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # --- STEP 2: DELETE DOCUMENTS FROM EACH STORE, THEN DELETE STORE ---
    print("\n--- Step 2: Deleting Vector Stores ---")
    try:
        stores = list(gemini_client.file_search_stores.list())
        print(f"Found {len(stores)} stores.")
        
        for store in stores:
            print(f"\n   Store: {store.name} ({store.display_name})")
            
            # List documents in this store
            try:
                docs = list(gemini_client.file_search_stores.documents.list(parent=store.name))
                print(f"   Found {len(docs)} documents.")
                
                # Delete each document with force=True
                for doc in docs:
                    try:
                        gemini_client.file_search_stores.documents.delete(
                            name=doc.name,
                            config=types.DeleteDocumentConfig(force=True)
                        )
                        print(f"      ✅ Deleted doc: {doc.name}")
                    except Exception as e:
                        print(f"      ❌ Failed: {e}")
                        
            except Exception as e:
                print(f"   ⚠️ Could not list documents: {e}")
            
            # Now delete the empty store
            try:
                gemini_client.file_search_stores.delete(name=store.name)
                print(f"   ✅ Store deleted!")
            except Exception as e:
                print(f"   ❌ Store delete failed: {e}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n✨ Cleanup Complete.")

if __name__ == "__main__":
    force_cleanup()