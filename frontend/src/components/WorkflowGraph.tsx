"use client";

/**
 * Lightweight visual representation of the LangGraph DAG states.
 * In production this would be driven by real-time WebSocket events.
 */

const NODES = [
  { id: "planner", label: "Planner", desc: "Permission & memory check" },
  { id: "sanitizer", label: "PII Sanitizer", desc: "Presidio redaction" },
  { id: "tool_decision", label: "Tool Decision", desc: "Write vs read-only" },
  { id: "hitl", label: "HITL Gate", desc: "Human interrupt if needed" },
  { id: "execution", label: "Execution", desc: "Run + audit log" },
];

interface Props {
  activeNode?: string;
  status?: string;
}

export function WorkflowGraph({ activeNode, status }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2 py-2">
      {NODES.map((node, idx) => {
        const isActive = activeNode === node.id;
        const isPast =
          activeNode &&
          NODES.findIndex((n) => n.id === activeNode) > idx;
        return (
          <div key={node.id} className="flex items-center gap-2">
            <div
              className={`px-3 py-2 rounded-lg border text-center min-w-[100px] ${
                isActive
                  ? "border-blue-500 bg-blue-500/20 text-blue-200"
                  : isPast
                  ? "border-emerald-600/50 bg-emerald-900/20 text-emerald-300"
                  : "border-slate-600 bg-slate-800 text-slate-400"
              }`}
            >
              <p className="text-xs font-medium">{node.label}</p>
              <p className="text-[10px] opacity-70">{node.desc}</p>
            </div>
            {idx < NODES.length - 1 && (
              <span className="text-slate-600 text-sm">→</span>
            )}
          </div>
        );
      })}
      {status && (
        <span className="ml-2 text-xs text-slate-500">Status: {status}</span>
      )}
    </div>
  );
}
