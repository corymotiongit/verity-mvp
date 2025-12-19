"""Script para limpiar datos locales y crear nuevo store."""
import os
import sys
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from google import genai
from dotenv import load_dotenv
import time

# Load env
load_dotenv(".env.local")
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY not found")
    sys.exit(1)

client = genai.Client(api_key=api_key)
org_id = "veritytest-organization0000"

print("=== CREAR NUEVO FILE SEARCH STORE ===\n")

# Create a new store
print("1. Creating new store...")
try:
    from google.genai import types
    
    operation = client.file_search_stores.create(
        config=types.CreateFileSearchStoreConfig(
            display_name=f"{org_id} File Search Store v2"
        )
    )
    
    # Wait for creation
    max_wait = 60
    waited = 0
    while not operation.done and waited < max_wait:
        time.sleep(2)
        waited += 2
        try:
            operation = client.operations.get(operation)
        except:
            pass
    
    new_store = operation.result
    print(f"   ✓ New store created!")
    print(f"\n   NEW STORE ID: {new_store.name}")
    print(f"\n   Update this in:")
    print(f"   - src/verity/modules/agent/router.py")
    print(f"   - src/verity/modules/documents/router.py")
    
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Clean local uploads
print("\n2. Cleaning local uploads folder...")
uploads_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
if os.path.exists(uploads_dir):
    for f in os.listdir(uploads_dir):
        fpath = os.path.join(uploads_dir, f)
        if os.path.isfile(fpath):
            os.remove(fpath)
            print(f"   Deleted: {f}")
    print("   ✓ Uploads cleaned")
else:
    print("   No uploads folder found")

print("\n=== DONE ===")
print("\nRESTART the backend server to use the new store!")
