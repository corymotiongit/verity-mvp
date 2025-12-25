"""Legacy guard-clause smoke test.

Legacy used to be frozen in `legacy_frozen/` with modules that raise on import.
That directory has now been removed. This script simply verifies it is absent.
"""

import os

if os.path.exists("legacy_frozen"):
    raise SystemExit("❌ legacy_frozen/ still exists")

print("✅ legacy_frozen/ is removed")
