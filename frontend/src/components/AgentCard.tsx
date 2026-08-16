"use client";

interface AgentCardProps {
  agent: {
    id: string;
    name: string;
    description?: string;
    model_name: string;
    requires_approval: boolean;
    approval_threshold_usd: number;
  };
  onRun: () => void;
  isSelected?: boolean;
}

export function AgentCard({ agent, onRun, isSelected }: AgentCardProps) {
  return (
    <div
      className={`bg-slate-800 border rounded-xl p-5 transition ${
        isSelected ? "border-blue-500" : "border-slate-700"
      }`}
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-medium text-white">{agent.name}</h3>
          {agent.description && (
            <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">
              {agent.description}
            </p>
          )}
        </div>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700 text-slate-300 font-mono">
          {agent.model_name}
        </span>
      </div>

      <div className="mt-4 flex items-center gap-3 text-xs text-slate-400">
        <span>
          HITL: {agent.requires_approval ? "On" : "Off"}
        </span>
        <span>·</span>
        <span>Threshold ${agent.approval_threshold_usd}</span>
      </div>

      <button
        onClick={onRun}
        className="mt-4 w-full py-2 rounded-lg bg-slate-700 hover:bg-blue-600 text-sm text-white transition"
      >
        Run with current query
      </button>
    </div>
  );
}
