"use client";

import { useState } from "react";

interface PendingItem {
  thread_id: string;
  agent_id: string;
  query: string;
  sanitized_query?: string;
  estimated_cost_usd: number;
  interrupt_reason?: string;
  status: string;
}

interface Props {
  item: PendingItem;
  onClose: () => void;
  onDecide: (decision: "approve" | "reject", comment?: string) => Promise<void>;
}

export function HumanApprovalModal({ item, onClose, onDecide }: Props) {
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(decision: "approve" | "reject") {
    setSubmitting(true);
    try {
      await onDecide(decision, comment || undefined);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-slate-800 border border-slate-600 rounded-2xl shadow-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Human Approval Required</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-xl leading-none"
          >
            ×
          </button>
        </div>

        <div className="px-6 py-5 space-y-4">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide">Original Query</p>
            <p className="mt-1 text-sm text-white">{item.query}</p>
          </div>

          {item.sanitized_query && item.sanitized_query !== item.query && (
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wide">
                After PII Sanitization
              </p>
              <p className="mt-1 text-sm text-slate-300 font-mono">
                {item.sanitized_query}
              </p>
            </div>
          )}

          {item.interrupt_reason && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2">
              <p className="text-xs text-amber-300">{item.interrupt_reason}</p>
            </div>
          )}

          <div className="flex gap-6 text-sm">
            <div>
              <p className="text-xs text-slate-500">Estimated Cost</p>
              <p className="text-lg font-semibold text-amber-400">
                ${item.estimated_cost_usd.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Thread</p>
              <p className="text-xs font-mono text-slate-400 mt-1">
                {item.thread_id}
              </p>
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-500">Reviewer comment (optional)</label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={2}
              className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-900 border border-slate-600 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Reason for decision…"
            />
          </div>
        </div>

        <div className="px-6 py-4 border-t border-slate-700 flex gap-3 justify-end">
          <button
            onClick={() => submit("reject")}
            disabled={submitting}
            className="px-4 py-2 rounded-lg bg-red-600/90 hover:bg-red-500 text-sm font-medium text-white disabled:opacity-50"
          >
            Reject
          </button>
          <button
            onClick={() => submit("approve")}
            disabled={submitting}
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-sm font-medium text-white disabled:opacity-50"
          >
            {submitting ? "Submitting…" : "Approve & Execute"}
          </button>
        </div>
      </div>
    </div>
  );
}
