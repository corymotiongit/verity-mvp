#!/usr/bin/env python3
"""
Test Suite: Legacy Isolation Verification

Verifica que el código legacy esté completamente aislado y no pueda ser
usado accidentalmente desde el código activo.
"""
import sys
import subprocess
import os

def test_guard_clauses():
    """Test que los guard clauses previenen imports"""
    print("\n🔒 Testing guard clauses...")
    
    test_code = """
import sys
sys.path.append('legacy_frozen')
try:
    from doc_qa_agent import DocQAAgent
    print("FAIL: Import succeeded")
    sys.exit(1)
except RuntimeError as e:
    if "LEGACY CODE IS FROZEN" in str(e):
        print("PASS: Guard clause working")
        sys.exit(0)
    else:
        print(f"FAIL: Wrong error: {e}")
        sys.exit(1)
"""
    
    result = subprocess.run(
        [sys.executable, "-c", test_code],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("   ✅ Guard clauses OK")
        return True
    else:
        print(f"   ❌ Guard clause test failed: {result.stdout} {result.stderr}")
        return False

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

def test_legacy_dir_outside_src():
    """Test que legacy_frozen está fuera de src/"""
    print("\n📁 Checking legacy directory location...")
    
    if os.path.exists("legacy_frozen") and not os.path.exists("src/verity/modules/_legacy"):
        print("   ✅ Legacy correctly isolated outside src/")
        return True
    else:
        print("   ❌ Legacy directory structure incorrect")
        return False

def test_no_pycache_in_legacy():
    """Test que no hay __pycache__ en legacy_frozen"""
    print("\n🗑️  Checking for __pycache__ in legacy...")
    
    if os.path.exists("legacy_frozen/__pycache__"):
        print("   ❌ __pycache__ found in legacy_frozen/")
        return False
    else:
        print("   ✅ No __pycache__ in legacy_frozen/")
        return True

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 LEGACY ISOLATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_legacy_dir_outside_src,
        test_no_pycache_in_legacy,
        test_guard_clauses,
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
