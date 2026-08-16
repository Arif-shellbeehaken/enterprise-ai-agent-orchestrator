"use client";

import { useEffect, useState } from "react";
import { listAgents, listAuditLogs, listPendingApprovals } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState({
    agents: 0,
    pending: 0,
    completed: 0,
    failed: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [agents, pending, logs] = await Promise.all([
          listAgents().catch(() => []),
          listPendingApprovals().catch(() => []),
          listAuditLogs().catch(() => []),
        ]);
        setStats({
          agents: agents.length,
          pending: pending.length,
          completed: logs.filter((l: any) => l.status === "COMPLETED").length,
          failed: logs.filter((l: any) =>
            ["FAILED", "REJECTED"].includes(l.status)
          ).length,
        });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const cards = [
    { label: "Active Agents", value: stats.agents, color: "text-blue-400" },
    { label: "Pending Approvals", value: stats.pending, color: "text-amber-400" },
    { label: "Completed Runs", value: stats.completed, color: "text-emerald-400" },
    { label: "Failed / Rejected", value: stats.failed, color: "text-red-400" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white mb-1">Executive Dashboard</h1>
      <p className="text-sm text-slate-400 mb-8">
        Real-time overview of agent activity and HITL governance
      </p>

      {loading ? (
        <p className="text-slate-500">Loading metrics…</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {cards.map((c) => (
            <div
              key={c.label}
              className="bg-slate-800 border border-slate-700 rounded-xl p-5"
            >
              <p className="text-xs text-slate-400 uppercase tracking-wide">
                {c.label}
              </p>
              <p className={`text-3xl font-bold mt-2 ${c.color}`}>{c.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="mt-10 bg-slate-800/60 border border-slate-700 rounded-xl p-6">
        <h2 className="text-sm font-medium text-slate-300 mb-3">Platform Notes</h2>
        <ul className="text-sm text-slate-400 space-y-2 list-disc list-inside">
          <li>All agent inputs are PII-sanitized via Microsoft Presidio before LLM dispatch.</li>
          <li>Actions above the approval threshold automatically pause for human review.</li>
          <li>Full audit trail with tenant isolation (Row-Level Security ready).</li>
          <li>LangGraph stateful graphs support interrupt / resume for HITL gates.</li>
        </ul>
      </div>
    </div>
  );
}
