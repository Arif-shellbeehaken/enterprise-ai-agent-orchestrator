/**
 * Axios / Fetch client with auth interceptors.
 */

const API_BASE =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function setAuth(token: string, meta?: { user_id: string; tenant_id: string; role: string }) {
  localStorage.setItem("access_token", token);
  if (meta) {
    localStorage.setItem("user_id", meta.user_id);
    localStorage.setItem("tenant_id", meta.tenant_id);
    localStorage.setItem("role", meta.role);
  }
}

export function clearAuth() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user_id");
  localStorage.removeItem("tenant_id");
  localStorage.removeItem("role");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    clearAuth();
    if (typeof window !== "undefined") {
      window.location.href = "/";
    }
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// Auth
export async function login(email: string, password: string) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Login failed");
  }
  const data = await res.json();
  setAuth(data.access_token, {
    user_id: data.user_id,
    tenant_id: data.tenant_id,
    role: data.role,
  });
  return data;
}

export async function register(email: string, password: string, role = "Operator") {
  return request("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, role }),
  });
}

// Agents
export async function listAgents() {
  return request<any[]>("/api/v1/agents");
}

export async function createAgent(payload: {
  name: string;
  description?: string;
  system_prompt: string;
  model_name?: string;
  requires_approval?: boolean;
  approval_threshold_usd?: number;
}) {
  return request("/api/v1/agents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// Workflows / HITL
export async function runWorkflow(agentId: string, query: string) {
  return request<{
    thread_id: string;
    status: string;
    interrupt_reason?: string;
    execution_result?: string;
    audit_id?: string;
    needs_approval: boolean;
  }>("/api/v1/workflows/run", {
    method: "POST",
    body: JSON.stringify({ agent_id: agentId, query }),
  });
}

export async function listPendingApprovals() {
  return request<
    {
      thread_id: string;
      agent_id: string;
      query: string;
      sanitized_query?: string;
      estimated_cost_usd: number;
      interrupt_reason?: string;
      status: string;
    }[]
  >("/api/v1/workflows/pending");
}

export async function decideApproval(
  threadId: string,
  decision: "approve" | "reject",
  comment?: string
) {
  return request("/api/v1/workflows/approve", {
    method: "POST",
    body: JSON.stringify({ thread_id: threadId, decision, comment }),
  });
}

// Audit
export async function listAuditLogs(status?: string) {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<any[]>(`/api/v1/audit/logs${q}`);
}
