# Enterprise AI Agent Orchestrator MVP

[![CI](https://github.com/Arif-shellbeehaken/enterprise-ai-agent-orchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/Arif-shellbeehaken/enterprise-ai-agent-orchestrator/actions/workflows/ci.yml)


**Product Requirement Document implementation** — full-stack platform for deploying autonomous AI agents with strict Human-in-the-Loop (HITL) governance, PII anonymization, multi-tenant audit logging, and LangGraph stateful orchestration.

Designed against the 2026 stack targets (Next.js 16+ / FastAPI 0.141+ / LangGraph 0.2+) using current stable package equivalents.

---

## Architecture Overview

| Layer | Technology | Role |
|-------|------------|------|
| Frontend | Next.js 15 + React 19 + Tailwind | Governance dashboard, approval queue, agent management |
| Backend API | FastAPI + Pydantic v2 | Async REST, JWT auth, RBAC |
| Orchestration | LangGraph | Stateful agent graphs with interrupt gates |
| LLM Gateway | LiteLLM | Unified access to Gemini / Claude / OpenAI |
| Data | PostgreSQL + pgvector-ready | Multi-tenant storage + vector memory |
| PII | Microsoft Presidio (+ regex fallback) | Real-time sanitization before LLM dispatch |
| Observability | Langfuse-ready | Trace & cost tracking hooks |

### LangGraph Node Pipeline

```
Planner → PII Sanitizer → Tool Decision → Human Approval Gate → Execution & Audit
```

- If estimated cost > threshold (default $100) **or** the action is a sensitive write, the graph pauses at the HITL gate.
- Frontend receives the pending item; a human Approves / Rejects; execution resumes (or is cancelled) and an audit row is written.

---

## Repository Layout

```
orchestrator-root/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth.py          # JWT + registration
│   │   │   ├── agents.py        # Agent CRUD
│   │   │   ├── workflows.py     # Run + HITL approve/reject
│   │   │   └── audit.py         # Governance log queries
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   ├── engine/
│   │   │   ├── graph_builder.py # LangGraph with interrupt
│   │   │   ├── pii_sanitizer.py # Presidio integration
│   │   │   └── tools_adapter.py # Salesforce / ERP / webhook stubs
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── agent.py
│   │   │   └── audit_log.py
│   │   └── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/app/
│   │   ├── dashboard/page.tsx
│   │   ├── agents/page.tsx
│   │   ├── workflows/page.tsx   # Approval queue
│   │   └── layout.tsx
│   ├── src/components/
│   │   ├── AgentCard.tsx
│   │   ├── HumanApprovalModal.tsx
│   │   └── WorkflowGraph.tsx
│   ├── src/lib/api.ts
│   └── package.json
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16/17 (optional for first boot — tables auto-create; in-memory fallback used for HITL threads in demo)

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Optional: download spaCy model for Presidio
python -m spacy download en_core_web_sm

# Configure
cp .env.example .env
# Edit DATABASE_URL, SECRET_KEY, GOOGLE_API_KEY etc.

uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open http://localhost:3000

### 3. First-time flow

1. Register an Admin user (or use the login form).
2. Create an Agent with a system prompt.
3. Run a query such as `Process a $250 payout to vendor X` — it should land in the **Approvals** queue.
4. Open the modal, Approve or Reject; the audit log is updated.

---

## Environment Variables (Backend)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://orchestrator:orchestrator@localhost:5432/orchestrator` | Async Postgres URL |
| `SECRET_KEY` | (dev placeholder) | JWT signing key — **change in production** |
| `GOOGLE_API_KEY` | — | Gemini via LiteLLM |
| `APPROVAL_THRESHOLD_USD` | `100` | Global HITL cost gate |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated |

---

## Security & Compliance Highlights

- **PII Sanitizer** runs on every inbound query before any LLM or tool call. Emails, phones, cards, SSNs and API-key patterns are redacted.
- **JWT + RBAC** (`Admin` / `Manager` / `Operator`). Agent creation restricted to Admin/Manager; approval available to all authenticated roles.
- **Tenant isolation** on every query (`tenant_id` filter). Schema is RLS-ready for Postgres policies.
- **Full audit trail** with status machine: `PENDING_APPROVAL → APPROVED/REJECTED → COMPLETED/FAILED`.

---

## Production Notes

- Replace the in-memory LangGraph checkpointer / thread store with a Postgres-backed checkpointer.
- Wire real LiteLLM calls inside `planner_node` and tool-calling.
- Enable Langfuse for token & latency observability.
- Add Alembic migrations instead of `create_all`.
- Deploy backend behind an API gateway; frontend on Vercel / similar.
- Configure real Salesforce / ERP credentials in `tools_adapter.py`.

---

## License

Internal / enterprise use. Built from the Enterprise AI Agent Orchestrator PRD v2.0 (2026).
