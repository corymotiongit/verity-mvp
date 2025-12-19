# Verity MVP - Frontend Specification for AI Development

## Project Overview

**Verity** is a multi-organization document management platform with AI-powered search and a conversational agent called **Veri**. The application needs a modern, premium frontend that communicates with a FastAPI backend.

### Core Concepts

1. **Multi-Organization**: Each organization has isolated data (documents, conversations, approvals)
2. **Agent Veri**: AI assistant that searches documents and proposes changes (never writes directly to DB)
3. **Human Approvals**: Any changes proposed by the agent require human approval
4. **Audit Trail**: Complete history of all actions (immutable)
5. **Role-Based Access**: user, approver, auditor, admin, owner

---

## Technology Requirements

### Recommended Stack
- **Framework**: Next.js 14+ with App Router OR Vite + React
- **Styling**: Vanilla CSS or CSS Modules (NO Tailwind unless requested)
- **State Management**: Zustand or React Context
- **HTTP Client**: Fetch API or Axios
- **Charts**: Vega-Lite (primary) or Chart.js
- **Auth**: Supabase Auth with WhatsApp OTP

---

## 🎨 Visual Design System

### Design Philosophy
- **Style**: "Startup moderno" minimalista tipo file explorer (sidebar + content)
- **Layout**: Grises como base (neutral), con highlights cálidos
- **Effects**: Glows sutiles SOLO para estados/acciones importantes (hover, selected, status)
- **Spacing**: UI limpia, mucho whitespace, bordes suaves, sombras suaves
- **Modes**: Light + Dark mode (switch persistente en localStorage)
- **Responsive**: Mobile + Desktop (navegación adaptativa)

### Color Palette Rules

#### ✅ ALLOWED Colors
```css
:root {
  /* ═══════════════════════════════════════════════════════════════════
     BASE GRAYS - Primary palette for backgrounds, surfaces, borders
     ═══════════════════════════════════════════════════════════════════ */
  
  /* Dark Mode */
  --bg-base: #0f0f12;           /* Deepest background */
  --bg-surface: #18181c;        /* Cards, panels */
  --bg-elevated: #1f1f24;       /* Modals, dropdowns */
  --bg-hover: #27272c;          /* Hover states */
  --bg-active: #2f2f35;         /* Active/selected */
  
  --border-subtle: rgba(255, 255, 255, 0.06);
  --border-default: rgba(255, 255, 255, 0.10);
  --border-strong: rgba(255, 255, 255, 0.16);
  
  --text-primary: #fafafa;
  --text-secondary: #a1a1aa;
  --text-muted: #71717a;
  --text-disabled: #52525b;
  
  /* Light Mode */
  --bg-base-light: #fafafa;
  --bg-surface-light: #ffffff;
  --bg-elevated-light: #ffffff;
  --bg-hover-light: #f4f4f5;
  --bg-active-light: #e4e4e7;
  
  --border-subtle-light: rgba(0, 0, 0, 0.06);
  --border-default-light: rgba(0, 0, 0, 0.10);
  --border-strong-light: rgba(0, 0, 0, 0.16);
  
  --text-primary-light: #18181b;
  --text-secondary-light: #52525b;
  --text-muted-light: #71717a;

  /* ═══════════════════════════════════════════════════════════════════
     ACCENT COLORS - Use sparingly for actions and states
     ═══════════════════════════════════════════════════════════════════ */
  
  /* Success / Primary Action - Emerald Green */
  --accent-success: #10b981;
  --accent-success-hover: #059669;
  --accent-success-glow: rgba(16, 185, 129, 0.25);
  
  /* Warning / Attention - Amber */
  --accent-warning: #f59e0b;
  --accent-warning-hover: #d97706;
  --accent-warning-glow: rgba(245, 158, 11, 0.25);
  
  /* Danger / Error - Red */
  --accent-danger: #ef4444;
  --accent-danger-hover: #dc2626;
  --accent-danger-glow: rgba(239, 68, 68, 0.25);
  
  /* Info / Neutral accent - Cyan tenue (must NOT look blue) */
  --accent-info: #67e8f9;        /* Very light cyan, almost white */
  --accent-info-hover: #22d3ee;
  --accent-info-glow: rgba(103, 232, 249, 0.15);
  
  /* ═══════════════════════════════════════════════════════════════════
     STATUS COLORS - For pills, badges, indicators
     ═══════════════════════════════════════════════════════════════════ */
  
  --status-pending: #fbbf24;     /* Amber - waiting */
  --status-processing: #67e8f9;  /* Cyan - in progress */
  --status-ready: #10b981;       /* Green - complete */
  --status-failed: #ef4444;      /* Red - error */
  --status-rejected: #f87171;    /* Light red */
  --status-approved: #34d399;    /* Light green */
}
```

#### 🚫 PROHIBITED Colors
- **Blue saturated** (`#3b82f6`, `#2563eb`, etc.) - NO usar
- **Purple/Violet** (`#8b5cf6`, `#7c3aed`, `#6366f1`) - NO usar
- **Indigo** (`#4f46e5`, `#6366f1`) - NO usar

#### Glow Effects (Usar con moderación)
```css
/* Solo aplicar en estados importantes */
.status-ready {
  box-shadow: 0 0 12px var(--accent-success-glow);
}

.button-primary:hover {
  box-shadow: 0 0 20px var(--accent-success-glow);
}

/* Glow muy sutil, nunca dominante */
```

### Typography
```css
:root {
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  
  --text-xs: 0.75rem;    /* 12px */
  --text-sm: 0.875rem;   /* 14px */
  --text-base: 1rem;     /* 16px */
  --text-lg: 1.125rem;   /* 18px */
  --text-xl: 1.25rem;    /* 20px */
  --text-2xl: 1.5rem;    /* 24px */
  --text-3xl: 1.875rem;  /* 30px */
}
```

### Spacing & Radius
```css
:root {
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
  
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;
}
```

---

## Authentication Flow

### Supabase with WhatsApp OTP

```javascript
// Step 1: Request OTP via WhatsApp
const { data, error } = await supabase.auth.signInWithOtp({
  phone: '+5215512345678',  // Mexican phone number example
  options: {
    channel: 'whatsapp'  // Use WhatsApp instead of SMS
  }
});

// Step 2: Verify OTP code
const { data: session, error: verifyError } = await supabase.auth.verifyOtp({
  phone: '+5215512345678',
  token: '123456',  // 6-digit code from WhatsApp
  type: 'sms'  // Use 'sms' type even for WhatsApp
});

// Step 3: Get access token for API calls
const token = (await supabase.auth.getSession()).data.session?.access_token;

// Include in all API requests
headers: {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
}
```

### Auth States
| State | Action |
|-------|--------|
| `idle` | Show phone input form |
| `sending` | Disable form, show spinner |
| `code_sent` | Show OTP input, start 60s countdown |
| `verifying` | Disable OTP input, show spinner |
| `error` | Show error message, allow retry |
| `authenticated` | Redirect to dashboard based on role |

### User Roles
| Role | Permissions |
|------|-------------|
| `user` | Basic access to documents and agent chat |
| `approver` | Can approve/reject changes |
| `auditor` | Can view audit logs |
| `admin` | Full org access |
| `owner` | Org owner, can manage roles |

---

## API Endpoints Reference

**Base URL**: `http://localhost:8000` (dev) or your production URL

### Common Response Headers
- `X-Request-ID`: Unique ID for tracing requests

### Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {},
    "request_id": "uuid"
  }
}
```

---

## 📄 Documents Module

### POST `/documents/ingest`
Upload a document to the organization's storage.

**Request** (multipart/form-data):
```
file: <binary file>
display_name: "Company Policy 2024" (optional)
metadata: '{"category": "policy"}' (optional JSON string)
```

**Response** (201):
```json
{
  "id": "uuid",
  "display_name": "Company Policy 2024",
  "gemini_uri": "files/abc123",
  "mime_type": "application/pdf",
  "size_bytes": 102400,
  "status": "processing" | "ready" | "failed",
  "metadata": {"category": "policy"},
  "created_at": "2024-01-15T10:30:00Z",
  "created_by": "uuid"
}
```

**Supported File Types**: PDF, TXT, MD, CSV, DOCX, PPTX, XLSX, HTML, JSON, XML

### GET `/documents`
List organization's documents.

**Query Parameters**:
- `page_size`: int (default: 20, max: 100)
- `page_token`: string (for pagination)

**Response**:
```json
{
  "items": [DocumentResponse],
  "meta": {
    "total_count": 45,
    "page_size": 20,
    "next_page_token": "abc123",
    "has_more": true
  }
}
```

### GET `/documents/{document_id}`
Get single document metadata.

### DELETE `/documents/{document_id}`
Delete a document (204 No Content).

### POST `/documents/search`
Semantic search across organization's documents.

**Request**:
```json
{
  "query": "What is the vacation policy?",
  "document_ids": ["uuid1", "uuid2"],  // optional, limit search
  "max_results": 5
}
```

**Response**:
```json
{
  "results": [
    {
      "document_id": "uuid",
      "document_name": "HR Policy.pdf",
      "snippet": "...employees are entitled to 20 days...",
      "relevance_score": 0.92
    }
  ],
  "request_id": "uuid"
}
```

---

## 🤖 Agent Module (Veri)

### POST `/agent/chat`
Chat with Veri agent.

**Request**:
```json
{
  "message": "What is the process for requesting vacation?",
  "conversation_id": "uuid",  // optional, null for new conversation
  "context": {
    "document_ids": ["uuid1"],  // optional, focus on specific docs
    "include_db_context": true
  }
}
```

**Response**:
```json
{
  "request_id": "uuid",
  "conversation_id": "uuid",
  "message": {
    "role": "assistant",
    "content": "Based on the HR Policy document, the vacation request process is..."
  },
  "sources": [
    {
      "type": "document",
      "id": "doc-uuid",
      "title": "HR Policy 2024.pdf",
      "snippet": "...vacation requests must be submitted...",
      "relevance": 0.95
    }
  ],
  "proposed_changes": null,
  "chart_spec": null
}
```

**Important Rules**:
- `sources[]` is ALWAYS returned (may be empty)
- `proposed_changes` is only returned when agent suggests DB changes
- `chart_spec` is ONLY returned when user EXPLICITLY asks for a chart

### Proposed Changes Example
When agent proposes a change:
```json
{
  "proposed_changes": [
    {
      "entity_type": "employee",
      "entity_id": "uuid",
      "action": "update",
      "changes": {
        "vacation_days": 25
      },
      "requires_approval": true
    }
  ]
}
```

### Chart Spec Example
When user asks "show me a chart of sales":
```json
{
  "chart_spec": {
    "type": "vega-lite",
    "spec": {
      "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
      "data": {"values": [{"month": "Jan", "sales": 100}]},
      "mark": "bar",
      "encoding": {
        "x": {"field": "month"},
        "y": {"field": "sales", "type": "quantitative"}
      }
    }
  }
}
```

### GET `/agent/conversations`
List user's conversations.

**Response**:
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Vacation Policy Discussion",
      "message_count": 5,
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T11:30:00Z"
    }
  ],
  "meta": {...}
}
```

### GET `/agent/conversations/{conversation_id}`
Get full conversation with messages.

**Response**:
```json
{
  "id": "uuid",
  "title": "Vacation Policy Discussion",
  "messages": [
    {
      "role": "user",
      "content": "What is the vacation policy?",
      "timestamp": "2024-01-15T10:00:00Z",
      "request_id": null
    },
    {
      "role": "assistant",
      "content": "Based on the documents...",
      "timestamp": "2024-01-15T10:00:05Z",
      "request_id": "uuid"
    }
  ],
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T11:30:00Z"
}
```

---

## ✅ Approvals Module

### POST `/approvals`
Create approval request (typically from agent proposed_changes).

**Request**:
```json
{
  "entity_type": "employee",
  "entity_id": "uuid",
  "fields": [
    {
      "field_name": "vacation_days",
      "original_value": 20,
      "proposed_value": 25
    }
  ],
  "reason": "Seniority adjustment",
  "priority": "normal"  // low, normal, high, urgent
}
```

**Response** (201):
```json
{
  "id": "uuid",
  "entity_type": "employee",
  "entity_id": "uuid",
  "status": "pending",
  "fields": [
    {
      "field_name": "vacation_days",
      "original_value": 20,
      "proposed_value": 25,
      "status": "pending",
      "approved_by": null,
      "approved_at": null,
      "comment": null
    }
  ],
  "reason": "Seniority adjustment",
  "priority": "normal",
  "created_at": "2024-01-15T10:00:00Z",
  "created_by": "uuid",
  "updated_at": null
}
```

### GET `/approvals/pending`
List pending approvals (for approvers dashboard).

### GET `/approvals`
List all approvals with optional filter.

**Query Parameters**:
- `status`: "pending" | "approved" | "rejected" | "partial"
- `page_size`, `page_token`

### GET `/approvals/{approval_id}`
Get approval with diff visualization.

**Response** (includes diff):
```json
{
  ...ApprovalResponse,
  "diff": {
    "vacation_days": {
      "before": 20,
      "after": 25,
      "diff_html": "<del>20</del> <ins>25</ins>"
    }
  }
}
```

### PATCH `/approvals/{approval_id}/fields/{field_name}`
Approve or reject a specific field (requires approver role).

**Request**:
```json
{
  "status": "approved",  // or "rejected"
  "comment": "Looks correct based on policy"
}
```

---

## 📊 Charts Module

### POST `/charts/generate`
Generate a chart specification.

**Request**:
```json
{
  "data": [
    {"month": "Jan", "sales": 100},
    {"month": "Feb", "sales": 150}
  ],
  "chart_type": "bar",  // bar, line, pie, scatter, area, auto
  "title": "Monthly Sales",
  "format": "vega-lite",  // or "chartjs"
  "save": false  // true to persist
}
```

**Response** (200 if not saved, 201 if saved):
```json
{
  "spec": {...vega-lite spec...},
  "format": "vega-lite",
  "saved": false
}
```

### GET `/charts`
List saved charts.

### GET `/charts/{chart_id}`
Get a saved chart.

### DELETE `/charts/{chart_id}`
Delete a chart.

---

## 📋 Reports Module

### POST `/reports`
Create a new report.

**Request**:
```json
{
  "title": "Q4 Financial Summary",
  "content": "...",
  "type": "financial",
  "metadata": {}
}
```

### GET `/reports`
List reports.

### GET `/reports/{report_id}`
Get report by ID.

### DELETE `/reports/{report_id}`
Delete report (admin only).

---

## 📜 Audit Module (Admin/Auditor Only)

### GET `/audit/timeline`
Get audit event timeline.

**Query Parameters**:
- `action`: "create" | "update" | "delete" | "approve" | "reject" | "upload" | "download" | "search" | "login" | "logout"
- `actor_id`: UUID
- `since`: ISO datetime
- `until`: ISO datetime
- `page_size`, `page_token`

**Response**:
```json
{
  "items": [
    {
      "id": "uuid",
      "action": "update",
      "entity_type": "employee",
      "entity_id": "uuid",
      "actor_id": "uuid",
      "payload": {...changes...},
      "ip_address": "192.168.1.1",
      "user_agent": "...",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "meta": {...}
}
```

### GET `/audit/entity/{entity_type}/{entity_id}`
Get history for specific entity.

---

## 🩺 Health Check

### GET `/health`
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "features": {
    "documents": true,
    "agent": true,
    "approvals": true,
    "charts": true,
    "reports": true,
    "audit": true
  }
}
```

## 📱 Screen Specifications

### 1. Login (WhatsApp OTP)

**Route**: `/login`

**Components**:
- Phone number input with country code selector
- "Enviar código" button
- OTP input (6 digits, auto-advance)
- "Verificar" button
- Error messages inline

**States**:
| State | UI Behavior |
|-------|-------------|
| `idle` | Form ready for input |
| `sending` | Phone input disabled, spinner on button |
| `code_sent` | Show OTP input, start countdown timer |
| `verifying` | OTP disabled, spinner on verify button |
| `error` | Show error message, allow retry |
| `success` | Redirect to dashboard based on role |

**Flow**:
```
[Phone Input] → "Enviar código" → [OTP Input] → "Verificar" → Dashboard
```

---

### 2. Global Layout (Desktop)

**Structure**:
```
┌─────────────────────────────────────────────────────────────┐
│                        TOPBAR                                │
│  [🔍 Search (cmd+k)]  [+ Upload]  [🌙/☀️]  [👤 Profile]     │
├────────────┬────────────────────────────────────────────────┤
│  SIDEBAR   │                   MAIN CONTENT                  │
│            │                                                 │
│  🏠 Home   │                                                 │
│  📁 Files  │                                                 │
│    ├ All   │                                                 │
│    └ Private│                                                │
│  🔒 Shared │   (Content area - varies by route)             │
│  ✅ Approvals│                                               │
│  📊 Reports │                                                │
│  📜 Audit  │                                                 │
│  📋 Logs   │                                                 │
│  ⚙️ Settings│                                                │
│            │                                                 │
└────────────┴────────────────────────────────────────────────┘
```

**Sidebar Navigation** (role-based visibility):
| Item | Route | Roles |
|------|-------|-------|
| Home | `/` | all |
| Files (All) | `/files` | all |
| Private Files | `/files/private` | all |
| Shared | `/files/shared` | all (placeholder MVP) |
| Chat (Veri) | `/chat` | all |
| Approvals | `/approvals` | admin, approver |
| Reports | `/reports` | all |
| Audit | `/audit` | admin, auditor |
| Logs | `/logs` | admin only |
| Team | `/settings/team` | admin, owner |
| Settings | `/settings` | all |
| Profile | `/profile` | all (from user menu) |

**Topbar Components**:
- **Search (cmd+k)**: Opens SpotlightSearch modal
- **Upload (+)**: Opens file upload modal
- **Theme Toggle**: Light/Dark mode switch (persist to localStorage)
- **Profile Menu**: User avatar, org name, org switcher (if multi-org), logout

**Mobile Layout**:
- Sidebar collapses to hamburger menu
- Bottom navigation bar for key items
- Search becomes top bar with icon

---

### 3. Files (Main View)

**Route**: `/files`

**Layout**:
```
┌─────────────────────────────────────────┬──────────────────┐
│ 📁 Files                    [+ Upload]  │   Detail Drawer  │
├─────────────────────────────────────────┤   (when file     │
│ [All] [PDFs] [Docs] [Sheets] [Images]   │    selected)     │
├─────────────────────────────────────────┤                  │
│                                         │  📄 filename.pdf │
│  ┌─────────────────────────────────┐   │  ──────────────  │
│  │ 🔲 Drag & drop files here       │   │  Size: 1.2 MB    │
│  │    or click to upload           │   │  Type: PDF       │
│  └─────────────────────────────────┘   │  Status: ● Ready │
│                                         │  Uploaded: 2h ago│
│  ☐ │ 📄 │ Contract_2024.pdf  │ PDF │...│                  │
│  ☐ │ 📊 │ Budget_Q4.xlsx     │ XLS │...│  Tags: contract  │
│  ☐ │ 📝 │ Meeting_notes.docx │ DOC │...│                  │
│  ☐ │ 🖼️ │ Logo.png           │ IMG │...│  [🗑️ Delete]     │
│                                         │  [🔄 Reindex]    │
│  No files found.                        │  [📋 View Sources]│
│  [Upload your first document]           │                  │
└─────────────────────────────────────────┴──────────────────┘
```

**File Table Columns**:
| Column | Content |
|--------|---------|
| Checkbox | Multi-select for batch actions |
| Icon | File type icon (PDF, DOC, XLS, IMG, etc.) |
| Name | Display name (clickable → detail) |
| Type | MIME type badge |
| Size | Human-readable (KB, MB) |
| Date | Relative time (2h ago, Yesterday) |
| Status | Pill: `processing` / `ready` / `failed` |
| Menu | ⋮ Actions (view, delete, reindex) |

**Tabs/Filters**:
- All files
- Documents (.docx, .doc, .txt, .md)
- Spreadsheets (.xlsx, .csv)
- PDFs (.pdf)
- Images (.png, .jpg, .webp)
- Others

**Empty State**:
```
┌─────────────────────────────────┐
│         📂                      │
│   No files found                │
│                                 │
│   Upload your first document    │
│   to get started with Verity    │
│                                 │
│   [+ Upload Document]           │
└─────────────────────────────────┘
```

**Upload Dropzone**:
- Large drop area (desktop)
- Progress bar during upload
- Status: uploading → processing → ready
- Error handling with retry option

---

### 4. Document Detail

**Route**: `/files/{document_id}`

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ ← Back to Files                                              │
│                                                              │
│ 📄 Contract_2024.pdf                                         │
│ ● Ready  │  request_id: abc123-def456                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌─ AI Summary ────────────────────────────────────────────┐ │
│ │ [Generate Summary]                                       │ │
│ │                                                          │ │
│ │ (Summary content appears here after generation)         │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─ Key Fields Extracted ──────────────────────────────────┐ │
│ │ Contract Date: 2024-01-15                                │ │
│ │ Parties: Acme Corp, Client LLC                          │ │
│ │ Value: $50,000                                          │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─ Sources ───────────────────────────────────────────────┐ │
│ │ 📄 Page 3: "The total contract value of..."            │ │
│ │ 📄 Page 7: "Payment terms include..."                  │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ [💡 Propose DB Update]  (if user can suggest)               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Sections**:
1. **Header**: File name, status pill, request_id (copyable)
2. **AI Summary**: Button to generate, displays summary text
3. **Key Fields Extracted**: Structured data from document (if applicable)
4. **Sources**: List of snippets with page references
5. **Actions**: "Propose DB Update" button (creates approval request)

---

### 5. Chat with Veri (Agent)

**Route**: `/chat` or `/chat/{conversation_id}`

**Layout**:
```
┌────────────────┬────────────────────────────────────────────┐
│ Conversations  │                 Chat                        │
│                │                                             │
│ [+ New Chat]   │  ┌────────────────────────────────────┐    │
│                │  │ 👤 You                              │    │
│ 💬 Contract Q  │  │ What are the payment terms in the  │    │
│ 💬 Budget 2024 │  │ latest contract?                    │    │
│ 💬 HR Policy   │  └────────────────────────────────────┘    │
│                │                                             │
│                │  ┌────────────────────────────────────┐    │
│                │  │ 🤖 Veri                             │    │
│                │  │ Based on Contract_2024.pdf, the    │    │
│                │  │ payment terms are Net 30...        │    │
│                │  │                                     │    │
│                │  │ 📎 Sources:                        │    │
│                │  │ ┌──────────────────────────────┐   │    │
│                │  │ │ 📄 Contract_2024.pdf (p.7)   │   │    │
│                │  │ │ "Payment shall be made..."   │   │    │
│                │  │ └──────────────────────────────┘   │    │
│                │  │                                     │    │
│                │  │ [📋 Copy] [📊 Create Report]       │    │
│                │  └────────────────────────────────────┘    │
│                │                                             │
├────────────────┴────────────────────────────────────────────┤
│ Quick prompts:                                               │
│ [📝 Resume recent docs] [🔍 Find contracts] [💰 Top gastos] │
├─────────────────────────────────────────────────────────────┤
│ [Type your message...                           ] [Send ➤]  │
└─────────────────────────────────────────────────────────────┘
```

**Chat Features**:

**Message Bubbles**:
- User: Right-aligned, subtle background
- Assistant: Left-aligned, with avatar

**Agent Response ALWAYS includes**:
1. **Answer**: Main response text
2. **Sources**: Clickable cards with document snippets
3. **request_id**: Small text, copyable

**Action Buttons on Responses**:
- `[📋 Copy]` - Copy response text
- `[📊 Create Report]` - Generate report from response
- `[💡 Propose Change]` - If `proposed_changes` returned

**Quick Prompts** (suggestions):
- "Resume los docs más recientes"
- "Encuentra contratos con fecha X"
- "Dame top gastos por ramo"

**Proposed Changes Flow**:
When agent returns `proposed_changes`:
```
┌────────────────────────────────────────┐
│ 💡 Proposed Change                      │
│                                         │
│ Entity: employee                        │
│ Action: update                          │
│                                         │
│ vacation_days: 20 → 25                  │
│                                         │
│ [Create Approval Request]               │
└────────────────────────────────────────┘
```

**Inline Charts**:
When agent returns `chart_spec`, render Vega-Lite chart directly in chat.

---

### 6. Admin: Pending Approvals (Inbox)

**Route**: `/approvals`

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ ✅ Pending Approvals                        [All] [History] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 🟡 vacation_days update                    2h ago       │ │
│ │ Requested by: john@company.com                          │ │
│ │ Type: DB Update  │  Entity: employee                    │ │
│ │ Status: ● Pending                                       │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 🔴 URGENT: Contract correction             30m ago      │ │
│ │ Requested by: maria@company.com                         │ │
│ │ Type: Correction  │  Entity: contract                   │ │
│ │ Status: ● Pending                                       │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Approval Detail View** (modal or drawer):
```
┌─────────────────────────────────────────────────────────────┐
│ Approval Request #abc123                         [× Close]  │
├─────────────────────────────────────────────────────────────┤
│ Entity: employee (uuid-here)                                │
│ Requested by: john@company.com                              │
│ Reason: Seniority adjustment                                │
│ Priority: 🟡 Normal                                         │
├─────────────────────────────────────────────────────────────┤
│ Field Changes:                                              │
│                                                              │
│ ┌─ vacation_days ────────────────────────────────────────┐ │
│ │  Before: 20                                             │ │
│ │  After:  25                                             │ │
│ │  ────────────────────────────────────────────────────── │ │
│ │  Comment: [                                          ]  │ │
│ │                                                         │ │
│ │  [✅ Approve]  [❌ Reject]                              │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─ department ───────────────────────────────────────────┐ │
│ │  Before: "Sales"                                        │ │
│ │  After:  "Marketing"                                    │ │
│ │  Status: ✅ Approved by admin@company.com               │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ [Apply All Approved Fields]                                 │
└─────────────────────────────────────────────────────────────┘
```

**Key Features**:
- Per-field approve/reject with optional comment
- Diff visualization (before/after)
- Priority indicators (color + icon)
- History tab shows all completed approvals

---

### 7. Audit Timeline (Immutable)

**Route**: `/audit`

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ 📜 Audit Trail                                              │
├─────────────────────────────────────────────────────────────┤
│ Filters: [Date Range ▾] [Entity Type ▾] [Action ▾]         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ● 2024-01-15 14:32:05                                       │
│ │  upload │ document │ by john@company.com                  │
│ │  📄 Contract_2024.pdf                                     │
│ │                                                            │
│ ● 2024-01-15 14:30:12                                       │
│ │  search │ documents │ by maria@company.com                │
│ │  Query: "payment terms"                                   │
│ │                                                            │
│ ● 2024-01-15 13:45:00                                       │
│ │  approve │ approval │ by admin@company.com                │
│ │  Approval #abc123 - vacation_days: approved               │
│ │                                                            │
│ ● 2024-01-15 12:00:00                                       │
│ │  login │ user │ by john@company.com                       │
│ │  IP: 192.168.1.100                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Event Types** (with icons):
| Action | Icon | Description |
|--------|------|-------------|
| upload | 📤 | Document uploaded |
| search | 🔍 | Search performed |
| approve | ✅ | Field approved |
| reject | ❌ | Field rejected |
| update | ✏️ | Entity updated |
| delete | 🗑️ | Entity deleted |
| login | 🔐 | User logged in |
| logout | 🚪 | User logged out |

**Filters**:
- Date range picker
- Entity type dropdown
- Action type dropdown
- Actor (user) dropdown

---

### 8. Logs (Admin Only)

**Route**: `/logs`

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ 📋 System Logs                               [📋 Copy Logs] │
├─────────────────────────────────────────────────────────────┤
│ Status: 🟢 API Up │ Queue: 3 pending │ Last: req_abc123    │
├─────────────────────────────────────────────────────────────┤
│ Level: [All ▾] [Info] [Warn] [Error]    Since: [Last 1h ▾] │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [INFO] 14:32:05  File uploaded: Contract_2024.pdf       │ │
│ │ [INFO] 14:32:06  Ingestion started for file abc123      │ │
│ │ [WARN] 14:32:10  Slow response from Gemini API (3.2s)   │ │
│ │ [INFO] 14:32:12  Ingestion completed: ready             │ │
│ │ [ERROR] 14:33:00 Failed to process image.png: timeout   │ │
│ │ [INFO] 14:33:05  Search query: "payment terms"          │ │
│ │ [INFO] 14:33:06  Search completed, 3 results            │ │
│ │                                                          │ │
│ │                                                          │ │
│ │ █                                                        │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Features**:
- Terminal-style log viewer (read-only)
- Color-coded log levels: green=info, yellow=warn, red=error
- Copy all logs button
- Status chips: API status, queue length, last request_id
- Simple filters: level, time range (no dangerous operations)

---

### 9. Reports + Charts

**Route**: `/reports`

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Reports                                   [+ New Report] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Q4 Financial Summary                    Dec 15, 2024   │   │
│ │ Type: Financial  │  By: admin@company.com             │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Contract Analysis Report                Dec 10, 2024   │   │
│ │ Type: Analysis  │  By: maria@company.com              │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Report Detail View**:
- Full report content (markdown rendered)
- Embedded tables
- Embedded charts (Vega-Lite)
- Export options (PDF, markdown)

**Charts Rule**:
> ⚠️ Charts ONLY appear when user explicitly requests them.
> Charts do NOT persist by default. Toggle "Save chart" to persist.

---

### 10. Settings

**Route**: `/settings`

**Tabs**:

#### Organization Tab
```
┌─────────────────────────────────────────────────────────────┐
│ Organization Settings                                        │
├─────────────────────────────────────────────────────────────┤
│ Name: [Test Organization                              ]      │
│                                                              │
│ Plan: Free (placeholder)                                    │
│ [Upgrade Plan] (placeholder)                                │
│                                                              │
│ File Search Store ID:                                       │
│ fileSearchStores/abc123... (read-only, copy button)         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Integrations Tab
```
┌─────────────────────────────────────────────────────────────┐
│ Integrations                                                 │
├─────────────────────────────────────────────────────────────┤
│ WhatsApp                                                     │
│ Status: 🟢 Connected                                        │
│ [Disconnect]                                                │
│                                                              │
│ n8n Workflows                                               │
│ Status: 🔴 Not Connected                                    │
│ [Connect]                                                   │
│                                                              │
│ API Key                                                     │
│ Key: veri_****************************1234                  │
│ [Regenerate] [Copy]                                         │
└─────────────────────────────────────────────────────────────┘
```

---

### 11. Profile

**Route**: `/profile`

**Access**: From topbar user menu or Settings

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ 👤 My Profile                                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                                                          ││
│  │         ┌───────────┐                                   ││
│  │         │           │   Display Name                    ││
│  │         │   👤 JD   │   [John Doe                    ]  ││
│  │         │           │                                   ││
│  │         └───────────┘   Phone                           ││
│  │         [Change Avatar] +52 155 1234 5678 (verified ✓)  ││
│  │                                                          ││
│  │         Email (optional)                                ││
│  │         [john.doe@company.com                        ]  ││
│  │                                                          ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─ Your Roles ────────────────────────────────────────────┐│
│  │                                                          ││
│  │  ● admin     Full organization access                   ││
│  │  ● approver  Can approve/reject changes                 ││
│  │                                                          ││
│  │  (Roles are assigned by organization owner)             ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─ Preferences ───────────────────────────────────────────┐│
│  │                                                          ││
│  │  Theme:       [☀️ Light] [🌙 Dark] [💻 System]          ││
│  │  Language:    [Español ▾]                               ││
│  │  Timezone:    [America/Mexico_City ▾]                   ││
│  │                                                          ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  [Save Changes]                           [Logout]          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Sections**:
1. **Avatar + Basic Info**: Upload avatar, edit display name
2. **Contact**: Phone (read-only, verified via OTP), optional email
3. **Your Roles**: Display current roles (read-only for non-admins)
4. **Preferences**: Theme, language, timezone

---

### 12. Team Management (Admin/Owner Only)

**Route**: `/settings/team` or `/team`

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ 👥 Team Management                          [+ Invite User] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 👤 John Doe              admin, approver    [⋮ Manage]  │ │
│ │    john.doe@company.com  │  Active                      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 👤 Maria Garcia          user               [⋮ Manage]  │ │
│ │    +52 155 9876 5432     │  Active                      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 👤 Carlos López          auditor            [⋮ Manage]  │ │
│ │    carlos@company.com    │  Invited (pending)           │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Manage User Modal** (click ⋮):
```
┌─────────────────────────────────────────────────────────────┐
│ Manage User: Maria Garcia                       [× Close]   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Display Name: [Maria Garcia                              ]  │
│                                                              │
│ Roles:                                                      │
│ ☑ user       Basic access to documents and chat            │
│ ☐ approver   Can approve/reject proposed changes           │
│ ☐ auditor    Can view audit trail                          │
│ ☐ admin      Full organization access                      │
│                                                              │
│ Status: ● Active                                            │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ [Save Changes]              [🗑️ Remove from Organization]  │
└─────────────────────────────────────────────────────────────┘
```

**Invite User Modal**:
```
┌─────────────────────────────────────────────────────────────┐
│ Invite Team Member                              [× Close]   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Phone or Email:                                             │
│ [+52 155 ...                                             ]  │
│                                                              │
│ Initial Roles:                                              │
│ ☑ user                                                      │
│ ☐ approver                                                  │
│ ☐ auditor                                                   │
│ ☐ admin                                                     │
│                                                              │
│ Message (optional):                                         │
│ [Join our Verity workspace...                            ]  │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ [Send Invitation]                                           │
└─────────────────────────────────────────────────────────────┘
```

**Features**:
- List all org members with their roles
- Edit user roles (checkboxes)
- Invite new users via phone or email
- Remove users from organization
- Show invite status (active, pending, expired)

**Role Hierarchy** (who can manage whom):
| Actor | Can Manage |
|-------|------------|
| `owner` | Everyone including admins |
| `admin` | Users, approvers, auditors (not other admins) |
| Others | Only their own profile |

---

## 🧩 Required UI Components

### Core Components

| Component | Description | Props |
|-----------|-------------|-------|
| `FileDropzone` | Drag & drop upload area | `onFilesSelected`, `accept`, `multiple` |
| `SpotlightSearch` | cmd+k search modal | `onSearch`, `placeholder` |
| `EmptyState` | Empty list placeholder | `icon`, `title`, `description`, `action` |
| `StatusPill` | Status badge with glow | `status`, `size` |
| `Drawer` | Side panel for details | `isOpen`, `onClose`, `title`, `children` |
| `DiffViewer` | Before/after comparison | `before`, `after`, `fieldName` |
| `TerminalLogViewer` | Read-only log display | `logs`, `level` |
| `CopyButton` | Copy text to clipboard | `text`, `label` |
| `RoleGate` | Conditional render by role | `roles`, `children`, `fallback` |
| `ThemeToggle` | Light/dark mode switch | `theme`, `onToggle` |

### Status Values

```typescript
type DocumentStatus = 'processing' | 'ready' | 'failed';
type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'partial';
type Priority = 'low' | 'normal' | 'high' | 'urgent';
type UserRole = 'user' | 'approver' | 'auditor' | 'admin' | 'owner';
```

---

## ⚠️ MVP Scope Rules

### ✅ In Scope
- File upload and listing (flat, no folders)
- Chat with Veri agent
- Source citations in responses
- Approval workflow (field-level)
- Basic audit trail
- Light/dark mode
- Responsive design

### 🚫 Out of Scope (MVP)
- "Shared with me" (placeholder only)
- Complex folder hierarchy (use tags instead)
- Direct DB editing by users (everything goes through approvals)
- Agent writes to DB (agent is read-only, only proposes)
- Multi-language (English/Spanish only)
- Offline mode
- Real-time collaboration

---



---

## Local Development

### Backend
```bash
cd verity-mvp
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn verity.main:app --reload --port 8000
```

### Supabase
1. Create project at [supabase.com](https://supabase.com)
2. Run `supabase/schema.sql` in SQL Editor
3. Get project URL and anon key

### Environment Variables (Frontend)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

---

## Notes for AI Development

1. **Start with Chat UI**: The Veri chat interface is the core feature
2. **Always show sources**: Every agent response should display citation cards
3. **Proposed changes flow**: 
   - Agent returns `proposed_changes` → Show review card
   - User clicks "Create Approval" → POST to `/approvals`
4. **Charts**: Use Vega-Lite embed component to render `chart_spec`
5. **Error handling**: Display toast notifications for API errors
6. **Loading states**: Skeleton loaders for lists, typing indicator for chat

---

## Example API Calls

### Upload Document
```javascript
const formData = new FormData();
formData.append('file', file);
formData.append('display_name', 'My Document');

const response = await fetch(`${API_URL}/documents/ingest`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: formData
});
```

### Send Chat Message
```javascript
const response = await fetch(`${API_URL}/agent/chat`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: "What is the refund policy?",
    conversation_id: currentConversationId || null
  })
});

const data = await response.json();
// data.message.content - assistant's response
// data.sources - citations to display
// data.proposed_changes - if any changes proposed
// data.chart_spec - if chart was requested
```

### Approve a Field
```javascript
await fetch(`${API_URL}/approvals/${approvalId}/fields/${fieldName}`, {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    status: 'approved',
    comment: 'Verified against policy doc'
  })
});
```
