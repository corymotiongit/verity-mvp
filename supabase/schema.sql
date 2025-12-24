-- =============================================================================
-- Verity MVP - Supabase Schema
-- Multi-organization with isolated File Search stores
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Organizations
-- Each org has its own Gemini File Search store
-- =============================================================================
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    file_search_store_id TEXT,  -- Gemini File Search store name (e.g., 'fileSearchStores/abc123')
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_organizations_slug ON organizations(slug);

-- =============================================================================
-- User Profiles
-- Links auth.users to organization
-- =============================================================================
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    display_name TEXT,
    phone TEXT,
    avatar_url TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_profiles_org_id ON profiles(org_id);

-- =============================================================================
-- Users (Identity)
-- WhatsApp identity store (no OTP)
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wa_id TEXT UNIQUE NOT NULL,
    phone_number TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

CREATE INDEX idx_users_wa_id ON users(wa_id);

-- =============================================================================
-- User Roles
-- Role-based access control
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'approver', 'auditor', 'admin', 'owner')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, role)
);

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);

-- =============================================================================
-- Documents
-- Document metadata (actual files are in Gemini File Search)
-- =============================================================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes BIGINT,
    content_hash TEXT,
    gemini_file_name TEXT,  -- Reference in File Search store
    status TEXT DEFAULT 'processing' CHECK (status IN ('processing', 'ready', 'error')),
    metadata JSONB DEFAULT '{}',
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_org_id ON documents(org_id);
CREATE INDEX idx_documents_created_by ON documents(created_by);
CREATE INDEX idx_documents_status ON documents(status);

-- =============================================================================
-- Conversations
-- Agent chat history per user/org
-- =============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT,
    message_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_org_id ON conversations(org_id);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);

-- =============================================================================
-- Conversation Messages
-- Individual messages in conversations
-- =============================================================================
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]',
    request_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversation_messages_conversation_id ON conversation_messages(conversation_id);

-- =============================================================================
-- Approvals
-- Human approval workflow
-- =============================================================================
CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'partial')),
    original_values JSONB NOT NULL,
    proposed_values JSONB NOT NULL,
    field_approvals JSONB DEFAULT '{}',
    requested_by UUID REFERENCES auth.users(id),
    approved_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_approvals_org_id ON approvals(org_id);
CREATE INDEX idx_approvals_status ON approvals(status);

-- =============================================================================
-- Audit Events
-- Immutable audit trail (INSERT only, no UPDATE/DELETE)
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID,
    actor_id UUID REFERENCES auth.users(id),
    payload JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_events_org_id ON audit_events(org_id);
CREATE INDEX idx_audit_events_entity ON audit_events(entity_type, entity_id);
CREATE INDEX idx_audit_events_actor_id ON audit_events(actor_id);
CREATE INDEX idx_audit_events_created_at ON audit_events(created_at);

-- Prevent UPDATE and DELETE on audit_events
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit events are immutable. UPDATE and DELETE are not allowed.';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_events_immutable
    BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_modification();

-- =============================================================================
-- Row Level Security (RLS)
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;

-- Helper function to get user's org_id
CREATE OR REPLACE FUNCTION get_user_org_id()
RETURNS UUID AS $$
BEGIN
    RETURN (SELECT org_id FROM profiles WHERE id = auth.uid());
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Organizations: users can only see their own org
CREATE POLICY org_isolation ON organizations
    FOR ALL USING (id = get_user_org_id());

-- Profiles: users can only see profiles in their org
CREATE POLICY profile_org_isolation ON profiles
    FOR ALL USING (org_id = get_user_org_id());

-- User Roles: users can see roles in their org
CREATE POLICY roles_org_isolation ON user_roles
    FOR ALL USING (
        user_id IN (SELECT id FROM profiles WHERE org_id = get_user_org_id())
    );

-- Documents: users can only access documents in their org
CREATE POLICY documents_org_isolation ON documents
    FOR ALL USING (org_id = get_user_org_id());

-- Conversations: users can only access their own conversations
CREATE POLICY conversations_user_isolation ON conversations
    FOR ALL USING (user_id = auth.uid() AND org_id = get_user_org_id());

-- Conversation Messages: through conversation ownership
CREATE POLICY messages_user_isolation ON conversation_messages
    FOR ALL USING (
        conversation_id IN (
            SELECT id FROM conversations 
            WHERE user_id = auth.uid() AND org_id = get_user_org_id()
        )
    );

-- Approvals: org isolation
CREATE POLICY approvals_org_isolation ON approvals
    FOR ALL USING (org_id = get_user_org_id());

-- Audit Events: org isolation (read only for non-service role)
CREATE POLICY audit_org_isolation ON audit_events
    FOR SELECT USING (org_id = get_user_org_id());

-- =============================================================================
-- Service Role Policies (bypass RLS for backend)
-- =============================================================================

-- Allow service role full access
CREATE POLICY service_role_all_organizations ON organizations
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY service_role_all_profiles ON profiles
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY service_role_all_documents ON documents
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY service_role_all_conversations ON conversations
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY service_role_all_messages ON conversation_messages
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY service_role_all_approvals ON approvals
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY service_role_all_audit ON audit_events
    FOR ALL TO service_role USING (true) WITH CHECK (true);
