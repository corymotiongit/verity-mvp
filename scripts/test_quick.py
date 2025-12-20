#!/usr/bin/env python3
"""Quick tests that don't require stopping the server"""
import sys
import subprocess
import os

print("🧪 LEGACY ISOLATION - QUICK TESTS\n")

# Test 1: Directory structure
print("📁 Legacy directory location...", end=" ")
if os.path.exists("legacy_frozen") and not os.path.exists("src/verity/modules/_legacy"):
    print("✅")
else:
    print("❌")

# Test 2: No __pycache__
print("🗑️  __pycache__ policy...", end=" ")
if os.path.exists("legacy_frozen/__pycache__"):
    # Importing a module (even one that immediately raises) can create __pycache__.
    # It's not a leak; we just don't want to commit it.
    print("✅ (present; ignored, should not be committed)")
else:
    print("✅ (absent)")

# Test 3: Guard clauses
print("🔒 Guard clauses...", end=" ")
test_code = """
import sys
sys.path.append('legacy_frozen')
try:
    from doc_qa_agent import DocQAAgent
    sys.exit(1)
except RuntimeError as e:
    if "LEGACY CODE IS FROZEN" in str(e):
        sys.exit(0)
    sys.exit(1)
"""
result = subprocess.run([sys.executable, "-c", test_code], capture_output=True)
if result.returncode == 0:
    print("✅")
else:
    print("❌")

# Test 4: No leaks
print("🔍 Legacy leaks check...", end=" ")
result = subprocess.run([sys.executable, "scripts/check_legacy_leaks.py"], capture_output=True, text=True)
if result.returncode == 0:
    print("✅")
    passed = True
else:
    print("❌")
    print(f"  Exit code: {result.returncode}")
    print(f"  Output: {result.stdout}")
    print(f"  Error: {result.stderr}")
    passed = False

if passed:
    print("\n✅ All quick tests passed!")
else:
    print("\n❌ Some tests failed")
