"use client";

import { useCallback, useEffect, useState } from "react";
import { listPendingApprovals, decideApproval } from "@/lib/api";
import { HumanApprovalModal } from "@/components/HumanApprovalModal";

interface PendingItem {
  thread_id: string;
  agent_id: string;
  query: string;
  sanitized_query?: string;
  estimated_cost_usd: number;
  interrupt_reason?: string;
  status: string;
}

export default function WorkflowsPage() {
  const [pending, setPending] = useState<PendingItem[]>([]);
  const [selected, setSelected] = useState<PendingItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listPendingApprovals();
      setPending(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 8000);
    return () => clearInterval(id);
  }, [refresh]);

  async function handleDecision(decision: "approve" | "reject", comment?: string) {
    if (!selected) return;
    try {
      const res = await decideApproval(selected.thread_id, decision, comment);
      setMessage(`Decision recorded: ${res.status}`);
      setSelected(null);
      await refresh();
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-white">Human Approval Queue</h1>
          <p className="text-sm text-slate-400">
            Review and approve high-risk agent actions
          </p>
        </div>
        <button
          onClick={refresh}
          className="px-3 py-1.5 rounded-lg border border-slate-600 text-sm text-slate-300 hover:bg-slate-800"
        >
          Refresh
        </button>
      </div>

      {message && (
        <p className="mb-4 text-sm text-emerald-400 bg-emerald-950/30 px-3 py-2 rounded">
          {message}
        </p>
      )}
      {error && (
        <p className="mb-4 text-sm text-red-400 bg-red-950/30 px-3 py-2 rounded">
          {error}
        </p>
      )}

      {loading && pending.length === 0 ? (
        <p className="text-slate-500">Loading queue…</p>
      ) : pending.length === 0 ? (
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-10 text-center">
          <p className="text-slate-400">No pending approvals</p>
          <p className="text-xs text-slate-500 mt-1">
            Actions that exceed cost thresholds will appear here
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {pending.map((item) => (
            <button
              key={item.thread_id}
              onClick={() => setSelected(item)}
              className="w-full text-left bg-slate-800 border border-slate-700 hover:border-amber-500/50 rounded-xl p-4 transition"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-sm text-white font-medium truncate">
                    {item.query}
                  </p>
                  {item.sanitized_query && item.sanitized_query !== item.query && (
                    <p className="text-xs text-slate-500 mt-0.5 truncate">
                      Sanitized: {item.sanitized_query}
                    </p>
                  )}
                  {item.interrupt_reason && (
                    <p className="text-xs text-amber-400/90 mt-1">
                      {item.interrupt_reason}
                    </p>
                  )}
                </div>
                <div className="shrink-0 text-right">
                  <span className="inline-block px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-300">
                    ${item.estimated_cost_usd.toFixed(2)}
                  </span>
                  <p className="text-[10px] text-slate-500 mt-1 font-mono">
                    {item.thread_id.slice(0, 8)}…
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {selected && (
        <HumanApprovalModal
          item={selected}
          onClose={() => setSelected(null)}
          onDecide={handleDecision}
        />
      )}
    </div>
  );
}
