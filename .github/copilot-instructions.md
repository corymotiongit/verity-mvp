# Verity MVP - AI Agent Instructions

## Project Overview

**Verity** is a modular monolithic FastAPI + React/Vite application for multi-organization document management with an AI conversational agent ("Veri") powered by Gemini File Search.

- **Backend**: FastAPI (Python 3.11+), Gemini Developer API (NOT Vertex AI)
- **Frontend**: Vite + React + TypeScript
- **Auth**: Supabase JWT + WhatsApp OTP via n8n webhooks
- **Database**: Supabase (PostgreSQL with RLS)
- **Architecture**: Multi-org isolation with dedicated File Search stores per organization/project

---

## Critical System Invariants

⚠️ **Read [SYSTEM_INVARIANTS.md](../SYSTEM_INVARIANTS.md) before modifying data/query logic.**

### Non-Negotiable Rules

1. **Agent never writes to DB** → Only returns `proposed_changes[]` for human approval
2. **Row IDs required** → Tabular answers MUST include `row_ids` evidence (audit trail)
3. **Data source logging** → Always log: `logger.info(f"[run_table_query] Loading from {data_source}")` 
4. **No silent fallbacks** → Fail loudly with typed exceptions (`VerityException`)
5. **OpenAPI sync** → Never edit `openapi.json` manually (use `python scripts/sync_openapi.py`)

---

## Development Workflows

### Running the Backend

```powershell
# Activate venv
.venv\Scripts\activate

# Start server (development)
python -m uvicorn verity.main:app --host 127.0.0.1 --port 8001 --reload

# Or use convenience script:
.\start_verity.ps1  # Sets env vars + starts uvicorn
```

**Required Environment Variables** (`.env` or inline):
- `GEMINI_API_KEY` - Get from https://aistudio.google.com/app/apikey
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_SERVICE_KEY` - Service role key from Supabase

**Optional Dev Flags**:
- `AUTH_OTP_INSECURE_DEV_BYPASS=true` - Bypass OTP validation (local only)
- `LEGACY_COMPAT_ENABLED=false` - Disable `/agent/*` endpoints (use `/api/v2/*`)

### Running the Frontend

```bash
cd frontend
npm install
npm run dev  # Vite dev server on http://localhost:5173
```

### Testing

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_api.py -v

# Quick validation
python scripts/test_quick.py
```

### OpenAPI Sync (CRITICAL)

After modifying FastAPI routes/schemas:

```bash
python scripts/sync_openapi.py  # Regenerates openapi.json
```

**CI should fail if `openapi.json` is out of sync:**
```bash
python scripts/check_openapi_sync.py  # Exit 1 if drift detected
```

---

## Architecture Patterns

### Multi-Organization Isolation

Each organization has:
- **One default File Search store** (for documents without project)
- **N project-specific stores** (format: `{org_id}:{project_name}`)

**Cache Key Format**:
```python
# Internally cached as:
f"{org_id}"                  # Default org store
f"{org_id}:{project_name}"   # Project-specific store
```

**Code Reference**: [src/verity/core/gemini.py](../src/verity/core/gemini.py)

### API Versioning

| Version | Path | Status | Notes |
|---------|------|--------|-------|
| Legacy | `/agent/*`, `/otp/*` | ⚠️ Deprecated | Controlled by `LEGACY_COMPAT_ENABLED` |
| v2 | `/api/v2/*` | ✅ Active | New auth, query, metrics endpoints |

**When to use each**:
- **New features** → Always use `/api/v2/*`
- **Legacy compatibility** → Only if `LEGACY_COMPAT_ENABLED=true` (default)

### Exception Handling

**Always use typed exceptions** (never raise generic `Exception`):

```python
from verity.exceptions import (
    UnresolvedMetricException,  # Metric not found in dictionary
    NoTableMatchException,      # Table not in available_tables
    InvalidFilterException,     # Bad filter spec
    TypeMismatchException,      # NaN values or type errors
    EmptyResultException,       # Filters produce 0 rows (hard fail)
)

# Example:
if score < 85:
    raise UnresolvedMetricException(
        user_input=question,
        suggestions=[{"name": metric, "score": score}]
    )
```

**Code Reference**: [src/verity/exceptions.py](../src/verity/exceptions.py)

---

## Module Boundaries

```
src/verity/
├── main.py              # FastAPI app, middleware, exception handlers
├── config.py            # Settings + feature flags (pydantic-settings)
├── exceptions.py        # Typed exceptions (ALWAYS use these)
├── auth/                # JWT validation, user extraction
├── core/
│   ├── gemini.py        # Gemini API client, File Search store management
│   ├── organization.py  # Org repository (DB access)
│   └── supabase_client.py
├── modules/             # Legacy modules (if LEGACY_COMPAT_ENABLED)
│   ├── documents/
│   ├── agent/
│   └── ...
├── api/routes/          # v2 API routes
│   ├── auth_v2.py       # OTP request/validate
│   ├── query_v2.py      # Table queries
│   └── metrics_v2.py    # Observability metrics
├── tools/               # LLM tools (resolve_semantics, run_table_query, etc.)
└── observability/       # Metrics store, error tracking
```

---

## Frontend Design System

⚠️ **Read [FRONTEND_SPEC.md](../FRONTEND_SPEC.md) for complete design rules.**

### Color Palette Rules

**ALLOWED**:
- Grays (base palette): `#0f0f12`, `#18181c`, `#1f1f24` (dark mode)
- Accent success: `#10b981` (emerald green)
- Accent warning: `#f59e0b` (amber)
- Accent danger: `#ef4444` (red)
- Accent info: `#67e8f9` (light cyan, NOT blue)

**FORBIDDEN** (never use):
- ❌ Saturated blue (`#3b82f6`, `#2563eb`)
- ❌ Purple/violet (`#8b5cf6`, `#7c3aed`)
- ❌ Indigo (`#4f46e5`, `#6366f1`)

**Glow effects**: Only on hover/active states, never dominant.

---

## Common Tasks

### Adding a New API Endpoint

1. Create route in `src/verity/api/routes/` (v2 preferred)
2. Define Pydantic schemas in the route file or `schemas.py`
3. Add route to `main.py` via `app.include_router()`
4. **CRITICAL**: Run `python scripts/sync_openapi.py`
5. Test with `pytest tests/test_api.py`

### Adding a New Feature Flag

1. Add to `FeatureFlags` class in [src/verity/config.py](../src/verity/config.py):
   ```python
   class FeatureFlags(BaseSettings):
       model_config = SettingsConfigDict(env_prefix="FEATURE_")
       my_feature: bool = True  # Default enabled
   ```
2. Check flag in endpoint:
   ```python
   settings = get_settings()
   if not settings.features.my_feature:
       raise FeatureDisabledException("my_feature")
   ```

### Debugging Auth Issues

**OTP not working**:
1. Check n8n is up: `curl https://shadowcat.cloud/webhook/health`
2. Check Redis: `redis-cli -u $REDIS_URL KEYS "otp:*"`
3. Use dev bypass: `AUTH_OTP_INSECURE_DEV_BYPASS=true` (local only)

**JWT expired**:
- Default TTL: 15 min (`AUTH_ACCESS_TOKEN_TTL_SECONDS`)
- Frontend must re-authenticate via OTP

**See**: [docs/RUNBOOK_AUTH_DATA.md](../docs/RUNBOOK_AUTH_DATA.md)

### Modifying Query Logic

1. **Read [SYSTEM_INVARIANTS.md](../SYSTEM_INVARIANTS.md) first**
2. Modify `src/verity/tools/run_table_query.py` or `resolve_semantics.py`
3. Update cache key logic if parameters changed
4. Add logging: `logger.info(f"[run_table_query] ...")` for data source, truncation, etc.
5. Test with: `pytest tests/test_run_table_query.py tests/test_resolve_semantics.py`

---

## Deployment

### Local Development

```powershell
# Backend
.\start_verity.ps1

# Frontend (separate terminal)
cd frontend
npm run dev
```

### Production (Cloud Run)

```bash
# Build + deploy via Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Manual deployment
gcloud run deploy verity-api \
  --source . \
  --region us-central1 \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest
```

**See**: [cloudbuild.yaml](../cloudbuild.yaml)

---

## Key Files to Reference

| File | Purpose |
|------|---------|
| [README.md](../README.md) | Quick start, architecture overview |
| [SYSTEM_INVARIANTS.md](../SYSTEM_INVARIANTS.md) | Non-negotiable rules for data/query logic |
| [FRONTEND_SPEC.md](../FRONTEND_SPEC.md) | Design system, color rules, API contracts |
| [docs/RUNBOOK_AUTH_DATA.md](../docs/RUNBOOK_AUTH_DATA.md) | Auth troubleshooting, env vars |
| [pyproject.toml](../pyproject.toml) | Python dependencies, test config |
| [scripts/sync_openapi.py](../scripts/sync_openapi.py) | OpenAPI regeneration (run after route changes) |

---

## Anti-Patterns (AVOID)

❌ **Editing `openapi.json` manually** → Use `scripts/sync_openapi.py`  
❌ **Silent fallbacks** → Always fail loudly with typed exceptions  
❌ **Agent writes to DB** → Only return `proposed_changes[]`  
❌ **Missing `data_source` in output** → Always include in query responses  
❌ **Saturated blue/purple in UI** → Use grays + emerald/amber/red accents  
❌ **Raising generic `Exception`** → Use `VerityException` subclasses  
❌ **Bypassing cache key params** → Always include `order_by`, `limit`, `columns`  

---

## Questions?

1. Check project docs: `README.md`, `SYSTEM_INVARIANTS.md`, `FRONTEND_SPEC.md`
2. Review existing code patterns in `src/verity/`
3. Search tests for examples: `tests/test_*.py`
4. Consult [docs/RUNBOOK_AUTH_DATA.md](../docs/RUNBOOK_AUTH_DATA.md) for operational issues
