# Demo Snapshot — 2025-12-20

This snapshot captures a minimal, reproducible demo flow for Verity MVP after validating COMPARE_PERIODS end-to-end and passing the full test suite.

## Preconditions

- Python 3.11+
- Virtual env created and deps installed (see `scripts/setup.ps1` / `scripts/setup.sh`)

## Quick validation (recommended)

Run the full test suite:

- Windows (PowerShell):
  - `F:/Github-Projects/verity-mvp/.venv/Scripts/python.exe -m pytest -q`

Expected: all tests pass.

## Start API server

From repo root:

- `F:/Github-Projects/verity-mvp/.venv/Scripts/python.exe -m uvicorn verity.main:app --port 8000`

## Smoke checks

- Health:
  - `Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v2/health' -Method GET -UseBasicParsing | Select-Object StatusCode,Content`

## Demo: COMPARE_PERIODS → temporal series → chart

Send a compare query (example):

- `Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v2/query' -Method POST -ContentType 'application/json' -Body '{"question":"Compare total revenue this month vs last month","org_id":"demo"}' -UseBasicParsing | Select-Object StatusCode,Content`

What to look for in the response:

- `intent` should be `compare`.
- `checkpoints` should include (in order):
  - `semantic_resolution`
  - `run_table_query@1.0`
  - `build_chart@2.0`
- The `run_table_query@1.0` checkpoint output should represent a temporal series (multi-row) with a derived group-by column like `order_date__month`.
- The `build_chart@2.0` checkpoint output should include Plotly JSON (`data` + `layout`).

## Notes

- Warnings from third-party dependencies are filtered in pytest configuration to keep CI output clean; this does not change runtime behavior.
