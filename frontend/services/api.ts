/**
 * Verity API Client
 * 
 * Handles all communication with the FastAPI backend.
 * Includes Bearer token support via localStorage.
 */

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8001')
  .trim()
  .replace(/\/+$/, '');

const AUTH_TOKEN_STORAGE_KEY = 'verity_token';

export function setAuthToken(token: string | null): void {
  try {
    if (!token) {
      window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
      return;
    }
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  } catch {
    // ignore storage errors
  }
}

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
// v2 Auth API
// =============================================================================

export interface OtpValidateV2Response {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export const authV2Api = {
  otpValidate: async (wa_id: string, otp: string): Promise<OtpValidateV2Response> => {
    const res = await apiFetch<OtpValidateV2Response>('/api/v2/auth/otp/validate', {
      method: 'POST',
      body: JSON.stringify({ wa_id, otp }),
    });

    // Store short-lived JWT for subsequent API calls.
    setAuthToken(res.access_token);
    return res;
  },
};


// =============================================================================
// v2 Query API
// =============================================================================

export interface QueryV2Request {
  question: string;
  available_tables?: string[];
  context?: Record<string, any> | null;
}

export interface QueryV2Response {
  conversation_id: string;
  response: string;
  intent: string;
  confidence: number;
  checkpoints: Array<Record<string, any>>;
}

export const queryV2Api = {
  query: (question: string, context?: Record<string, any>): Promise<QueryV2Response> => {
    const payload: QueryV2Request = {
      question,
      // Keep the backend default unless we have a reason to override.
      context: context ?? null,
    };

    return apiFetch<QueryV2Response>('/api/v2/query', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
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
  approvals: approvalsApi,
  authV2: authV2Api,
  queryV2: queryV2Api,
  health: healthApi,
};

export default api;
