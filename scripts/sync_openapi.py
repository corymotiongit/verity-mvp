"""Sync repository openapi.json with the FastAPI application's generated OpenAPI.

Why:
- The repo ships a committed openapi.json.
- FastAPI generates the authoritative spec at runtime.
- Keeping them in sync avoids drift (e.g., missing /api/v2/*).

Usage:
  F:/Github-Projects/verity-mvp/.venv/Scripts/python.exe scripts/sync_openapi.py
"""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    # Importing the app will also import routers; keep side-effects minimal.
    from verity.main import app

    spec = app.openapi()

    out_path = Path("openapi.json")
    out_path.write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    paths = spec.get("paths", {}) or {}
    has_v2 = any(p.startswith("/api/v2/") for p in paths.keys())

    print(f"Wrote {out_path} ({len(paths)} paths). v2_present={has_v2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
