export type UserRole = 'user' | 'approver' | 'auditor' | 'admin' | 'owner';

export type DocumentStatus = 'processing' | 'ready' | 'failed';
export type ApprovalStatus = 'pending' | 'approved' | 'rejected';
export type ReportType = 'financial' | 'analysis' | 'compliance';
export type MemberStatus = 'active' | 'invited' | 'disabled';

export interface VerityDocument {
  id: string;
  display_name: string;
  mime_type: string;
  size_bytes: number;
  status: DocumentStatus;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface Conversation {
  id: string;
  title: string;
  last_message: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: SourceCitation[];
  request_id?: string;
  proposed_changes?: ProposedChange[];
  chart_spec?: any;
  table_source?: { columns: string[], rows: any[][], total_rows?: number };
  evidence_ref?: string;
}

export interface SourceCitation {
  type: 'document';
  id: string;
  title: string;
  snippet: string;
  relevance: number;
}

export interface ApprovalRequest {
  id: string;
  entity_type: string;
  entity_id: string;
  entity_name: string;
  requested_by: string;
  created_at: string;
  reason: string;
  status: ApprovalStatus;
  changes: FieldChange[];
}

export interface FieldChange {
  field_name: string;
  old_value: any;
  new_value: any;
  status: ApprovalStatus;
  comment?: string;
}

export interface ProposedChange {
  entity_type: string;
  entity_id: string;
  action: 'update' | 'create' | 'delete';
  changes: Record<string, any>;
  requires_approval: boolean;
}

export interface Report {
  id: string;
  title: string;
  type: ReportType;
  created_at: string;
  author: string;
  content: string; // Markdown
  chart_data?: any;
}

export interface AuditLog {
  id: string;
  action: 'upload' | 'search' | 'approve' | 'reject' | 'login' | 'update';
  actor: string;
  entity: string;
  details: string;
  timestamp: string;
}

export interface TeamMember {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  roles: UserRole[];
  status: MemberStatus;
  avatar_url?: string;
  joined_at: string;
}

export interface NavItem {
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: UserRole[];
}