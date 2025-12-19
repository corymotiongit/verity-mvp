# Verity MVP

Modular monolithic backend for multi-organization document management with AI-powered search and conversational agent.

## Architecture

- **Framework**: FastAPI (Python 3.11+)
- **LLM**: Gemini Developer API with File Search Tool
- **Auth**: Supabase JWT with multi-organization support
- **Database**: Supabase (PostgreSQL with RLS)
- **Isolation**: Each organization has its own File Search store

### Key Design Decisions

1. **Multi-Organization Isolation**: Each org has one File Search store
2. **Gemini Developer API** (not Vertex AI) - Simpler auth with API key
3. **File Search Tool** - Built-in RAG without custom embeddings
4. **Agent never writes to DB** - Only proposes changes via `proposed_changes[]`
5. **chart_spec only when explicit** - User must request charts explicitly
6. **sources[] always returned** - Full traceability with request_id

## Quick Start

### 1. Clone and Setup

```bash
cd verity-mvp
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e ".[dev]"
```

### 2. Configure API Key

Get your Gemini API key from: https://aistudio.google.com/app/apikey

Create `.env.local`:
```
GEMINI_API_KEY=your-api-key-here
```

### 3. Setup Supabase Database

Run the schema in your Supabase project:
```bash
# Copy contents of supabase/schema.sql to Supabase SQL Editor
```

### 4. Run Server

```bash
uvicorn verity.main:app --reload --port 8001
```

## Multi-Organization Architecture

### Database Schema

```sql
-- Organizations (1 File Search store per org)
organizations(id, name, slug, file_search_store_id, created_at)

-- User Profiles (linked to org)
profiles(id, org_id, display_name, phone, created_at)

-- User Roles
user_roles(user_id, role)  -- user, approver, auditor, admin, owner

-- Documents (org-scoped)
documents(id, org_id, display_name, filename, mime_type, gemini_file_name, ...)
```

### Isolation Flow

1. User authenticates via Supabase JWT
2. Backend resolves `org_id` from `profiles` table
3. Gets org's `file_search_store_id` from `organizations`
4. If no store exists, creates one on first document upload
5. All queries use org's store exclusively

### Row Level Security (RLS)

All tables have RLS policies ensuring users can only access their organization's data:

```sql
-- Documents: users can only access their org's documents
CREATE POLICY documents_org_isolation ON documents
    FOR ALL USING (org_id = get_user_org_id());
```

## 📁 Project-Based File Search Stores

Verity supports **project-based isolation** for documents. Each project gets its own dedicated File Search store, enabling:
- ✅ **Real API-level filtering** by project
- ✅ **Better organization** of documents  
- ✅ **Faster, more precise searches** (smaller index per project)
- ✅ **Scalability** (each project has its own index)

### Architecture

```
📁 Organización "Mi Empresa"
    │
    ├── 📦 Store Default (documentos sin proyecto)
    │       └── documento_general.pdf
    │
    ├── 📦 Store "Proyecto Alpha" 
    │       ├── contrato_alpha.pdf
    │       └── presupuesto_alpha.xlsx
    │
    └── 📦 Store "Proyecto Beta"
            ├── informe_beta.pdf
            └── rrhh_beta.docx
```

### How It Works

| Step | Action | Result |
|------|--------|--------|
| 1️⃣ | Upload document **WITH** project | Creates/uses project-specific store |
| 2️⃣ | Upload document **WITHOUT** project | Goes to organization's default store |
| 3️⃣ | Chat with project filter selected | Searches **ONLY** in that project's store |
| 4️⃣ | Chat with category filter | Uses prompt context to focus response |

### Filtering Levels

| Filter Type | Level | How It Works |
|-------------|-------|--------------|
| **Project** | API-level (real) | Separate File Search stores per project |
| **Category** | Prompt-level (soft) | Instruction added to prompt to focus on category |
| **Tags** | Metadata | Stored locally, displayed in UI |

### Store Key Format

Stores are cached internally using the format:
```
{org_id}                    → Default org store
{org_id}:{project_name}     → Project-specific store
```

## API Endpoints

### Documents Module
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/documents/ingest` | Upload file to org's File Search store |
| GET | `/documents/{id}` | Get document metadata |
| GET | `/documents` | List org's documents |
| POST | `/documents/search` | Search in org's store |
| DELETE | `/documents/{id}` | Delete document |

### Agent Module
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agent/chat` | Chat with Veri (org-scoped grounding) |
| GET | `/agent/conversations/{id}` | Get conversation |
| GET | `/agent/conversations` | List user's conversations |

### Other Modules
- `/approvals` - Human approval workflow
- `/charts` - Chart generation
- `/reports` - Report management
- `/forecast` - Forecasting
- `/logs` - Admin logs (read-only)
- `/audit` - Immutable audit trail

## Response Format

### Agent Chat Response
```json
{
  "request_id": "uuid",
  "conversation_id": "uuid",
  "message": {
    "role": "assistant",
    "content": "Response with org-specific context..."
  },
  "sources": [
    {"type": "document", "id": "...", "title": "...", "snippet": "..."}
  ],
  "proposed_changes": null,
  "chart_spec": null
}
```

## File Structure

```
verity-mvp/
├── src/verity/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── auth/                # JWT + multi-org auth
│   │   └── schemas.py       # User, Organization models
│   ├── core/
│   │   ├── gemini.py        # Gemini API + per-org stores
│   │   ├── organization.py  # Org repository
│   │   └── supabase_client.py
│   └── modules/
│       ├── documents/       # Org-isolated document management
│       ├── agent/           # Org-scoped AI grounding
│       └── ...
├── supabase/
│   └── schema.sql           # Full DB schema with RLS
└── ...
```

## Production Deployment

### Secret Manager Setup

```bash
# Store Gemini API key
echo -n "your-api-key" | gcloud secrets create gemini-api-key --data-file=-
```

### Cloud Run

```bash
gcloud run deploy verity-api \
  --source . \
  --region us-central1 \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest \
  --set-env-vars SUPABASE_URL=...,SUPABASE_SERVICE_ROLE_KEY=...
```

## User Roles

| Role | Permissions |
|------|-------------|
| `user` | Basic access to documents and agent |
| `approver` | Can approve/reject changes |
| `auditor` | Can view audit logs |
| `admin` | Full org access |
| `owner` | Org owner, can manage roles |

## Supported File Types

- PDF (.pdf)
- Text (.txt, .md)
- CSV (.csv)
- Word (.docx)
- PowerPoint (.pptx)
- Excel (.xlsx)
- HTML, JSON, XML

## License

Proprietary - All rights reserved.
