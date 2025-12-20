# scripts/check_legacy_leaks.py
import os
import sys

LEGACY_DIR_NAMES = {"legacy", "_legacy", "legacy_frozen"}
SRC_DIR = "src"

FORBIDDEN_IMPORT_KEYWORDS = [
    "CodeGeneratorAgent",
    "ChartAgent",
    "ForecastAgent",
    "DocQAAgent",
    "legacy",
    "_legacy",
    "legacy_frozen",
]

errors = []

def scan_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                stripped = line.strip()
                
                # Skip commented lines
                if stripped.startswith("#"):
                    continue
                
                # Skip docstrings
                if '"""' in stripped or "'''" in stripped:
                    continue
                
                # Skip explanatory comments about legacy
                if any(x in line for x in ["Moved to legacy", "LEGACY", "NO usa", "NO importar", 
                                           "legacy compatibility", "Was:", "Wrapper for"]):
                    continue
                
                for kw in FORBIDDEN_IMPORT_KEYWORDS:
                    if kw in line:
                        # Only report if it looks like actual code (import, class instantiation, etc.)
                        if any(x in line for x in ["import ", "from ", " = " + kw, "(" + kw]):
                            errors.append((path, i, kw, line.strip()))
    except Exception:
        pass

def scan_tree(root):
    for base, dirs, files in os.walk(root):
        for d in list(dirs):
            if d in LEGACY_DIR_NAMES and base.startswith(SRC_DIR):
                errors.append((os.path.join(base, d), "-", "LEGACY_DIR", "Legacy dir inside src"))
        for file in files:
            if file.endswith(".py"):
                scan_file(os.path.join(base, file))

if __name__ == "__main__":
    # Set UTF-8 encoding for Windows
    import sys
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    scan_tree(SRC_DIR)

    if errors:
        print("\n❌ LEGACY LEAKS DETECTED:\n")
        for e in errors:
            print(f"{e[0]}:{e[1]} -> {e[2]} | {e[3]}")
        sys.exit(1)
    else:
        print("✅ OK: No legacy leaks detected.")
