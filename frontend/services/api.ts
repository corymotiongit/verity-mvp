/**
 * Verity API Client
 * 
 * Handles all communication with the FastAPI backend.
 * Auth is currently mocked - token management will be added later.
 */

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8001')
  .trim()
  .replace(/\/+$/, '');

const AUTH_TOKEN_STORAGE_KEY = 'verity_token';

function getAuthToken(): string | null {
  try {
    return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

// Auth header if token exists
const getAuthHeaders = (): HeadersInit => {
  const token = getAuthToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

// Generic fetch wrapper with error handling
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message =
      errorData?.error?.message ||
      (typeof errorData?.error === 'string' ? errorData.error : null) ||
      (errorData?.ok === false && typeof errorData?.error === 'string' ? errorData.error : null) ||
      `API Error: ${response.status}`;
    throw new Error(message);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// =============================================================================
// Documents API
// =============================================================================

export interface DocumentResponse {
  id: string;
  display_name: string;
  gemini_uri: string;
  mime_type: string;
  size_bytes: number;
  status: 'processing' | 'ready' | 'failed';
  metadata: Record<string, any> | null;
  created_at: string;
  created_by: string;
}

export interface DocumentListResponse {
  items: DocumentResponse[];
  meta: {
    total_count: number;
    page_size: number;
    next_page_token: string | null;
    has_more: boolean;
  };
}

export interface SearchResult {
  document_id: string;
  document_name: string;
  snippet: string;
  relevance_score: number;
}

export interface DocumentSearchResponse {
  results: SearchResult[];
  request_id: string;
}

export const documentsApi = {
  list: (pageSize = 20, pageToken?: string): Promise<DocumentListResponse> => {
    const params = new URLSearchParams({ page_size: String(pageSize) });
    if (pageToken) params.append('page_token', pageToken);
    return apiFetch(`/documents?${params}`);
  },

  get: (id: string): Promise<DocumentResponse> => {
    return apiFetch(`/documents/${id}`);
  },

  delete: (id: string): Promise<void> => {
    return apiFetch(`/documents/${id}`, { method: 'DELETE' });
  },

  getDownloadUrl: (id: string): string => {
    return `${API_BASE_URL}/documents/${id}/download`;
  },

  upload: async (file: File, displayName?: string, metadata?: Record<string, any>): Promise<DocumentResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    if (displayName) formData.append('display_name', displayName);
    if (metadata) formData.append('metadata', JSON.stringify(metadata));

    const response = await fetch(`${API_BASE_URL}/documents/ingest`, {
      method: 'POST',
      body: formData,
      // Don't set Content-Type header - browser will set it with boundary
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || 'Upload failed');
    }

    return response.json();
  },

  search: (query: string, documentIds?: string[], maxResults = 5): Promise<DocumentSearchResponse> => {
    return apiFetch('/documents/search', {
      method: 'POST',
      body: JSON.stringify({
        query,
        document_ids: documentIds,
        max_results: maxResults,
      }),
    });
  },

  getStoreInfo: (): Promise<{
    store_id: string | null;
    documents: Array<{
      name: string;
      display_name: string | null;
      state: string;
      create_time: string;
      update_time: string;
    }>;
    document_count: number;
    error?: string;
    message?: string;
  }> => {
    return apiFetch('/documents/store/info');
  },

  getFilters: (): Promise<{
    categories: string[];
    projects: string[];
    tags: string[];
  }> => {
    return apiFetch('/documents/store/filters');
  },
};

// =============================================================================
// Agent API
// =============================================================================

export interface AgentChatRequest {
  message: string;
  conversation_id?: string | null;
  context?: {
    document_ids?: string[];
    include_db_context?: boolean;
    /** Filter documents by category (e.g., 'contrato', 'rrhh', 'finanzas') */
    document_category?: string;
    /** Filter documents by project - uses project-specific File Search store */
    document_project?: string;
  };
}

export interface SourceCitation {
  type: 'document' | 'database' | 'web';
  id: string;
  title: string | null;
  snippet: string | null;
  relevance: number | null;
}

export interface ProposedChange {
  entity_type: string;
  entity_id: string | null;
  action: 'create' | 'update' | 'delete';
  changes: Record<string, any>;
  requires_approval: boolean;
}

export interface ChatScope {
  project: string | null;
  tag_ids: string[];
  category: string | null;
  period: string | null;
  source: string | null;
  collection_id: string | null;
  doc_ids: string[];
  mode: 'filtered' | 'all_docs' | 'empty';
}

export interface ScopeSuggestion {
  label: string;
  action: 'upload' | 'clear_filters' | 'select_all' | 'select_project';
  project_id?: string | null;
}

export interface ResolvedScope {
  display_summary: string;
  doc_count: number;
  requires_action: boolean;
  is_empty: boolean;
  empty_reason?: string | null;
  suggestion?: ScopeSuggestion | null;
}

export interface AgentChatResponse {
  request_id: string;
  conversation_id: string;
  message: {
    role: 'assistant';
    content: string;
  };
  sources: SourceCitation[];
  proposed_changes?: ProposedChange[] | null;
  chart_spec?: { type: string; spec: Record<string, any> } | null;
  table_preview?: Record<string, any> | null;
  evidence_ref?: string | null;
  scope_info?: ResolvedScope | null;
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  message_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  request_id: string | null;
  sources?: SourceCitation[] | null;
  chart_spec?: Record<string, any> | null;
  table_preview?: Record<string, any> | null;
  evidence_ref?: string | null;
}

export interface ConversationResponse {
  id: string;
  title: string | null;
  messages: ConversationMessage[];
  created_at: string;
  updated_at: string | null;
}

export const agentApi = {
  chat: (request: AgentChatRequest): Promise<AgentChatResponse> => {
    return apiFetch('/agent/chat', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  listConversations: (pageSize = 20, pageToken?: string) => {
    const params = new URLSearchParams({ page_size: String(pageSize) });
    if (pageToken) params.append('page_token', pageToken);
    return apiFetch<{
      items: ConversationSummary[];
      meta: { total_count: number; has_more: boolean };
    }>(`/agent/conversations?${params}`);
  },

  getConversation: (id: string): Promise<ConversationResponse> => {
    return apiFetch(`/agent/conversations/${id}`);
  },

  deleteConversation: (id: string): Promise<void> => {
    return apiFetch(`/agent/conversations/${id}`, { method: 'DELETE' });
  },

  getScope: (convId: string): Promise<ChatScope | null> => {
    return apiFetch(`/agent/chat/${convId}/scope`);
  },

  updateScope: (convId: string, scope: ChatScope): Promise<ChatScope> => {
    return apiFetch(`/agent/chat/${convId}/scope`, {
      method: 'PUT',
      body: JSON.stringify(scope),
    });
  },

  resolveScope: (convId: string): Promise<ResolvedScope> => {
    return apiFetch(`/agent/chat/${convId}/scope/resolve`, { method: 'POST' });
  },
};

// =============================================================================
// Approvals API
// =============================================================================

export interface FieldApproval {
  field_name: string;
  original_value: any;
  proposed_value: any;
  status: 'pending' | 'approved' | 'rejected';
  approved_by: string | null;
  approved_at: string | null;
  comment: string | null;
}

export interface ApprovalResponse {
  id: string;
  entity_type: string;
  entity_id: string;
  status: 'pending' | 'approved' | 'rejected' | 'partial';
  fields: FieldApproval[];
  reason: string | null;
  priority: string;
  created_at: string;
  created_by: string;
  updated_at: string | null;
}

export const approvalsApi = {
  listPending: (pageSize = 20) => {
    return apiFetch<{
      items: ApprovalResponse[];
      meta: { total_count: number; has_more: boolean };
    }>(`/approvals/pending?page_size=${pageSize}`);
  },

  list: (status?: string, pageSize = 20) => {
    const params = new URLSearchParams({ page_size: String(pageSize) });
    if (status) params.append('status', status);
    return apiFetch<{
      items: ApprovalResponse[];
      meta: { total_count: number; has_more: boolean };
    }>(`/approvals?${params}`);
  },

  get: (id: string): Promise<ApprovalResponse & { diff?: Record<string, any> }> => {
    return apiFetch(`/approvals/${id}`);
  },

  updateField: (
    approvalId: string,
    fieldName: string,
    status: 'approved' | 'rejected',
    comment?: string
  ): Promise<FieldApproval> => {
    return apiFetch(`/approvals/${approvalId}/fields/${fieldName}`, {
      method: 'PATCH',
      body: JSON.stringify({ status, comment }),
    });
  },
};

// =============================================================================
// OTP Auth API (n8n proxy)
// =============================================================================

export interface OtpRequestResponse {
  ok: boolean;
  userId?: string;
  phone?: string;
  expiresAt?: string;
  channel?: string;
  message?: string;
  debugOtp?: string;
  error?: string;
}

export interface OtpValidateResponse {
  ok: boolean;
  userId?: string;
  sessionToken?: string;
  expiresAt?: string;
  error?: string;
}

export const otpApi = {
  request: (userId: string, phone: string): Promise<OtpRequestResponse> => {
    return apiFetch('/otp/request', {
      method: 'POST',
      body: JSON.stringify({ userId, phone }),
    });
  },

  validate: (userId: string, otp: string): Promise<OtpValidateResponse> => {
    return apiFetch('/otp/validate', {
      method: 'POST',
      body: JSON.stringify({ userId, otp }),
    });
  },
};

// =============================================================================
// Health Check
// =============================================================================

export interface HealthResponse {
  status: string;
  version: string;
  features: Record<string, boolean>;
}

export const healthApi = {
  check: (): Promise<HealthResponse> => {
    return apiFetch('/health');
  },
};

// Export all APIs
export const api = {
  documents: documentsApi,
  agent: agentApi,
  approvals: approvalsApi,
  otp: otpApi,
  health: healthApi,
};

export default api;
