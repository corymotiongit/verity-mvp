#!/usr/bin/env python3
"""scripts/test_legacy_isolation.py

Legacy removal verification.

Antes, este repo congelaba agentes legacy en `legacy_frozen/` con guard clauses.
Ahora el objetivo es más simple: confirmar que legacy ya no existe en el repo,
que no hay fugas en `src/`, y que el server arranca sin depender de legacy.
"""
import sys
import subprocess
import os

def test_legacy_removed():
    """Test que legacy_frozen/ ya no existe"""
    print("\n📁 Checking legacy removal...")
    if os.path.exists("legacy_frozen"):
        print("   ❌ legacy_frozen/ still exists")
        return False
    print("   ✅ legacy_frozen/ is removed")
    return True

def test_no_leaks():
    """Test que no hay fugas de legacy en src/"""
    print("\n🔍 Checking for legacy leaks...")
    
    result = subprocess.run(
        [sys.executable, "scripts/check_legacy_leaks.py"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("   ✅ No leaks detected")
        return True
    else:
        print(f"   ❌ Leaks found:\n{result.stdout}")
        return False

def test_server_starts():
    """Test que el servidor puede arrancar sin legacy"""
    print("\n🚀 Testing server startup...")
    
    # Start server in background
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "verity.main:app", "--port", "8001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    import time
    time.sleep(5)  # Wait for startup
    
    # Check if running
    if proc.poll() is None:  # Still running
        print("   ✅ Server started successfully")
        proc.terminate()
        proc.wait()
        return True
    else:
        stdout, stderr = proc.communicate()
        print(f"   ❌ Server failed to start:\n{stderr}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 LEGACY ISOLATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_legacy_removed,
        test_no_leaks,
        test_server_starts,
    ]
    
    results = [test() for test in tests]
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTS: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("\n✅ ALL TESTS PASSED - Legacy is completely isolated!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED - Check output above")
        sys.exit(1)
