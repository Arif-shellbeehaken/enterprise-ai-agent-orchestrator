"use client";

import { useEffect, useState } from "react";
import { listAgents, createAgent, runWorkflow } from "@/lib/api";
import { AgentCard } from "@/components/AgentCard";

export default function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState(
    "You are a careful enterprise operations agent. Never execute financial transfers without confirmation."
  );
  const [query, setQuery] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<any>(null);
  const [error, setError] = useState("");

  async function refresh() {
    setLoading(true);
    try {
      const data = await listAgents();
      setAgents(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createAgent({
        name,
        system_prompt: prompt,
        requires_approval: true,
        approval_threshold_usd: 100,
      });
      setShowForm(false);
      setName("");
      await refresh();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleRun(agentId: string) {
    if (!query.trim()) return;
    setRunResult(null);
    setError("");
    try {
      const res = await runWorkflow(agentId, query);
      setRunResult(res);
      setSelectedAgent(agentId);
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-white">Agents</h1>
          <p className="text-sm text-slate-400">Create and manage autonomous agents</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white"
        >
          {showForm ? "Cancel" : "+ New Agent"}
        </button>
      </div>

      {error && (
        <p className="mb-4 text-sm text-red-400 bg-red-950/30 px-3 py-2 rounded">
          {error}
        </p>
      )}

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="mb-8 bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-4"
        >
          <div>
            <label className="text-xs text-slate-400">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-900 border border-slate-600 text-sm"
              required
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">System Prompt</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={3}
              className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-900 border border-slate-600 text-sm"
              required
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-sm text-white"
          >
            Create Agent
          </button>
        </form>
      )}

      {/* Quick run panel */}
      <div className="mb-8 bg-slate-800/60 border border-slate-700 rounded-xl p-5">
        <h2 className="text-sm font-medium text-slate-300 mb-3">Quick Run</h2>
        <div className="flex gap-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Update CRM record or process $250 payout"
            className="flex-1 px-3 py-2 rounded-lg bg-slate-900 border border-slate-600 text-sm"
          />
        </div>
        {runResult && (
          <div className="mt-4 p-3 rounded-lg bg-slate-900 border border-slate-600 text-sm">
            <p>
              <span className="text-slate-400">Status:</span>{" "}
              <span
                className={
                  runResult.needs_approval
                    ? "text-amber-400"
                    : "text-emerald-400"
                }
              >
                {runResult.status}
              </span>
            </p>
            {runResult.interrupt_reason && (
              <p className="mt-1 text-amber-300/90">{runResult.interrupt_reason}</p>
            )}
            {runResult.execution_result && (
              <p className="mt-1 text-slate-400 font-mono text-xs">
                {runResult.execution_result}
              </p>
            )}
            {runResult.needs_approval && (
              <p className="mt-2 text-xs text-blue-400">
                → Go to Approvals queue to review this run (thread: {runResult.thread_id})
              </p>
            )}
          </div>
        )}
      </div>

      {loading ? (
        <p className="text-slate-500">Loading agents…</p>
      ) : agents.length === 0 ? (
        <p className="text-slate-500">No agents yet. Create one to get started.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {agents.map((a) => (
            <AgentCard
              key={a.id}
              agent={a}
              onRun={() => handleRun(a.id)}
              isSelected={selectedAgent === a.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}
