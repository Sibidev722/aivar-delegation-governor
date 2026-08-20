import React from 'react';
import { 
  User, 
  Bot, 
  Cpu, 
  ShieldCheck, 
  Database, 
  ArrowRight, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  KeyRound,
  ShieldAlert
} from 'lucide-react';

export default function ChainVisualizer({ executionResult, activeTokens, isRunning }) {
  // If no execution result yet, provide default architectural topology
  const defaultNodes = [
    {
      id: "user",
      role: "Originating User",
      label: "USER-001",
      icon: User,
      scope: "Root Authority",
      dataScope: ["CUST-101", "CUST-102", "CUST-103", "CUST-104", "CUST-105"],
      depth: "-",
      status: "ACTIVE",
      type: "user"
    },
    {
      id: "agent_a",
      role: "Agent A (Coordinator)",
      label: "agent_a",
      icon: Bot,
      scope: "financials:read:all",
      dataScope: ["CUST-101", "CUST-102"],
      depth: 0,
      status: "VALID",
      type: "agent"
    },
    {
      id: "agent_b",
      role: "Agent B (Planner)",
      label: "agent_b",
      icon: Cpu,
      scope: "financials:read:summary",
      dataScope: ["CUST-101"],
      depth: 1,
      status: "VALID",
      type: "agent"
    },
    {
      id: "agent_c",
      role: "Agent C (Worker)",
      label: "agent_c",
      icon: Bot,
      scope: "financials:read:summary",
      dataScope: ["CUST-101"],
      depth: 2,
      status: "VALID",
      type: "agent"
    },
    {
      id: "governor",
      role: "Delegation Governor",
      label: "Policy Decision Point",
      icon: ShieldCheck,
      scope: "Enforce Dual Monotonicity",
      dataScope: ["All Authorized Boundaries"],
      depth: "PEP/PDP",
      status: "ACTIVE",
      type: "governor"
    },
    {
      id: "financial_tool",
      role: "Financial Tool Gateway",
      label: "MongoDB Financials",
      icon: Database,
      scope: "Protected Records",
      dataScope: ["Executed: CUST-101"],
      depth: "Tool",
      status: "PROTECTED",
      type: "tool"
    }
  ];

  // Dynamic status evaluation if an execution result exists
  const isBlocked = executionResult && (!executionResult.ok || executionResult.data?.status === "error" || executionResult.data?.decision === "DENY");
  const isAllowed = executionResult && executionResult.ok && (executionResult.data?.status === "completed" || executionResult.data?.status === "SUCCESS" || executionResult.data?.valid === true);

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            Live Delegation Chain Visualizer
          </h2>
          <p className="text-xs text-slate-400">
            Real-time multi-agent cryptographic token propagation and Policy Enforcement Point (PEP) evaluation
          </p>
        </div>

        {executionResult && (
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono font-semibold ${
            isAllowed 
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
              : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
          }`}>
            {isAllowed ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
            <span>{isAllowed ? "AUTHORIZATION: ALLOWED" : "AUTHORIZATION: REJECTED (BLOCKED)"}</span>
          </div>
        )}
      </div>

      {/* Graphical Chain Flow */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3 relative">
        {defaultNodes.map((node, idx) => {
          const Icon = node.icon;
          const isLast = idx === defaultNodes.length - 1;

          // Determine node border/glow styling based on execution status
          let cardStyle = "border-slate-700/80 bg-slate-900/60";
          let badgeColor = "bg-slate-800 text-slate-300 border-slate-700";

          if (isAllowed) {
            cardStyle = "border-emerald-500/40 bg-slate-900/90 shadow-lg shadow-emerald-950/30";
            badgeColor = "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
          } else if (isBlocked) {
            if (node.id === "governor" || node.id === "agent_c") {
              cardStyle = "border-rose-500/50 bg-rose-950/20 shadow-lg shadow-rose-950/40";
              badgeColor = "bg-rose-500/20 text-rose-400 border-rose-500/40";
            }
          }

          return (
            <div key={node.id} className="relative flex flex-col justify-between">
              <div className={`p-4 rounded-xl border transition-all duration-200 h-full flex flex-col justify-between ${cardStyle}`}>
                <div>
                  {/* Top: Node Icon & Role */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="p-2 rounded-lg bg-slate-800 border border-slate-700 text-sky-400">
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border bg-slate-800/80 text-slate-400 border-slate-700">
                      Depth: {node.depth}
                    </span>
                  </div>

                  <div className="mb-2">
                    <h3 className="text-xs font-semibold text-slate-200 truncate">{node.role}</h3>
                    <p className="text-[11px] font-mono text-emerald-400">{node.label}</p>
                  </div>

                  {/* Scopes & Data Boundaries */}
                  <div className="space-y-1.5 text-[11px] font-mono bg-slate-950/60 p-2 rounded-lg border border-slate-800/80">
                    <div>
                      <span className="text-slate-500 text-[10px] block">Scope:</span>
                      <span className="text-slate-300 break-all">{node.scope}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] block">Data Scope:</span>
                      <span className="text-amber-300 break-all">{Array.isArray(node.dataScope) ? node.dataScope.join(", ") : node.dataScope}</span>
                    </div>
                  </div>
                </div>

                {/* Bottom: Status Badge */}
                <div className="mt-3 pt-2 border-t border-slate-800 flex items-center justify-between">
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border font-semibold ${badgeColor}`}>
                    {node.status}
                  </span>
                  <KeyRound className="w-3.5 h-3.5 text-slate-500" />
                </div>
              </div>

              {/* Arrow separator on larger screens */}
              {!isLast && (
                <div className="hidden lg:flex absolute -right-3.5 top-1/2 -translate-y-1/2 z-10 p-1 rounded-full bg-slate-800 border border-slate-700 text-slate-400">
                  <ArrowRight className="w-3 h-3" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Execution Feedback Banner */}
      {executionResult && (
        <div className={`mt-6 p-4 rounded-xl border font-mono text-xs ${
          isAllowed 
            ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-200' 
            : 'bg-rose-950/20 border-rose-500/30 text-rose-200'
        }`}>
          <div className="flex items-center justify-between mb-1">
            <span className="font-bold flex items-center gap-1.5">
              {isAllowed ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <ShieldAlert className="w-4 h-4 text-rose-400" />}
              {isAllowed ? "DELEGATION PIPELINE SUCCESS" : `GOVERNANCE INTERCEPTION: ${executionResult.data?.error_code || "REJECTED"}`}
            </span>
            <span className="text-[11px] text-slate-400">HTTP Status: {executionResult.status || 200}</span>
          </div>
          <p className="text-slate-300 text-xs">
            {executionResult.data?.message || (isAllowed ? "Real end-to-end token chain validated with strict monotonic scope preservation." : JSON.stringify(executionResult.data))}
          </p>
        </div>
      )}
    </div>
  );
}
