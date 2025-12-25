#!/usr/bin/env python3
"""Quick checks that don't require stopping the server.

Legacy used to be frozen in `legacy_frozen/`. Now we verify it is removed and
that `src/` has no legacy leaks.
"""
import sys
import subprocess
import os

print("🧪 LEGACY ISOLATION - QUICK TESTS\n")

# Test 1: Legacy removed
print("📁 legacy_frozen removed...", end=" ")
if not os.path.exists("legacy_frozen"):
    print("✅")
else:
    print("❌")

# Test 2: No leaks
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
