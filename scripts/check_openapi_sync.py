"""Fail if openapi.json is out of sync with FastAPI's generated OpenAPI.

Rules:
- Do NOT edit openapi.json by hand.
- The spec is generated from the server (FastAPI app.openapi()).

Usage:
  python scripts/check_openapi_sync.py

Exit codes:
  0 - in sync
  1 - out of sync
"""

from __future__ import annotations

import json
from pathlib import Path


def _render_openapi(spec: dict) -> str:
    # Must match scripts/sync_openapi.py formatting so comparisons are stable.
    return json.dumps(spec, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    repo_path = Path("openapi.json")
    if not repo_path.exists():
        print("ERROR: openapi.json not found at repo root")
        return 1

    current = repo_path.read_text(encoding="utf-8")

    from verity.main import app

    generated = _render_openapi(app.openapi())

    if current == generated:
        print("OK: openapi.json is in sync with FastAPI")
        return 0

    print("ERROR: openapi.json is out of sync with FastAPI")
    print("Fix: run `python scripts/sync_openapi.py` and commit the updated openapi.json")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
