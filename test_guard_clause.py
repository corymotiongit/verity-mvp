import sys
sys.path.append('legacy_frozen')

try:
    from doc_qa_agent import DocQAAgent
    print("❌ ERROR: Legacy import succeeded - guard clause failed!")
except RuntimeError as e:
    print(f"✅ SUCCESS: Guard clause working - {e}")
except Exception as e:
    print(f"⚠️  Unexpected error: {e}")
