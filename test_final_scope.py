"""Test: Final Chat Scope & Diagnostics (Persistent)"""
import requests
import json
import uuid
import time
import io

BASE_URL = "http://localhost:8000"
ORG_ID = "00000000-0000-0000-0000-000000000100"
headers = {
    'X-Organization-ID': ORG_ID,
    'X-User-ID': '00000000-0000-0000-0000-000000000001'
}

chat_id = str(uuid.uuid4())
print(f"=== Test: Final Scope & Diagnostics (Chat: {chat_id}) ===\n")

# 1. Create Tag & Doc in Project 'Gamma'
print("1. Setup: Creating Tag and Doc in 'Gamma'...")
# Create Tag
r = requests.post(f"{BASE_URL}/tags", json={"name": "Importante", "project": "Gamma"}, headers=headers)
if r.status_code in [200, 201]:
    tag_id = r.json()["id"]
    print(f"   Created tag: {tag_id}")
else:
    print(f"   Failed to create tag: {r.text}")
    tag_id = None

# Create Doc
csv_content = "ID,VAL\n1,100"
files = {'file': ('gamma_doc.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')}
meta = {"project": "Gamma", "category": "Dataset"}
r = requests.post(f"{BASE_URL}/documents/ingest", files=files, data={'metadata': json.dumps(meta)}, headers=headers)
if r.status_code == 200:
    doc_id = r.json()['id']
    print(f"   Created doc: {doc_id}")
    
    # Assign Tag
    if tag_id:
        requests.post(f"{BASE_URL}/tags/documents/{doc_id}", json={"tag_ids": [tag_id]}, headers=headers)
        print("   Assigned tag 'Importante'")
else:
    print(f"   Failed to upload doc: {r.text}")
    doc_id = None

time.sleep(1)

# 2. Test Success Scope (Gamma)
if doc_id:
    print("\n2. Test: Success Scope (Project Gamma)...")
    r = requests.put(
        f"{BASE_URL}/agent/chat/{chat_id}/scope",
        json={"project": "Gamma", "mode": "filtered", "tag_ids": []},
        headers=headers
    )
    # Chat
    r = requests.post(f"{BASE_URL}/agent/chat", json={"conversation_id": chat_id, "message": "hello"}, headers=headers)
    info = r.json().get("scope_info", {})
    print(f"   Docs Found: {info.get('doc_count')}")
    if info.get("doc_count") > 0:
        print("   ✅ Found Gamma docs")
    else:
        print("   ❌ Failed to find Gamma docs")

# 3. Test Empty Project (Delta) -> Diagnostic
print("\n3. Test: Empty Project (Delta)...")
r = requests.put(
    f"{BASE_URL}/agent/chat/{chat_id}/scope",
    json={"project": "Delta", "mode": "filtered"},
    headers=headers
)
# Resolve explicitly to check diagnostic
r = requests.post(f"{BASE_URL}/agent/chat/{chat_id}/scope/resolve", headers=headers)
data = r.json()
print(f"   Reason: {data.get('empty_reason')}")
print(f"   Suggestion: {data.get('suggestion')}")

if "vacío" in str(data.get('empty_reason')):
    print("   ✅ Correctly diagnosed empty project")
else:
    print("   ❌ Diagnostic failed")

# Cleanup Skipped
print("\nCleanup skipped (file preserved for UI testing)...")
if doc_id:
    print(f"Document ID: {doc_id} created in Project 'Gamma'")
print("You can now verify this in the Frontend UI.")
