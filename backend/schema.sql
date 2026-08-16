-- Enterprise AI Agent Orchestrator – PostgreSQL schema
-- Matches PRD Module C + multi-tenant RLS readiness

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- CREATE EXTENSION IF NOT EXISTS vector;  -- enable when using pgvector memory

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'Operator',  -- Admin | Manager | Operator
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);

CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    system_prompt TEXT NOT NULL,
    model_name VARCHAR(100) DEFAULT 'gemini-2.0-flash',
    requires_approval BOOLEAN DEFAULT TRUE,
    approval_threshold_usd NUMERIC(10,2) DEFAULT 100.00,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agents_tenant ON agents(tenant_id);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    agent_id UUID REFERENCES agents(id),
    action_taken VARCHAR(255) NOT NULL,
    sanitized_input TEXT,
    execution_result TEXT,
    status VARCHAR(50) NOT NULL,  -- PENDING_APPROVAL | APPROVED | REJECTED | COMPLETED | FAILED
    reviewed_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_status ON audit_logs(status);

-- Example RLS policies (enable when ready)
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY tenant_isolation_users ON users USING (tenant_id = current_setting('app.tenant_id')::uuid);
-- ... similar for agents & audit_logs
