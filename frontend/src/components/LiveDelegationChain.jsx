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
  ShieldAlert,
  Loader2,
  Sparkles,
  Server
} from 'lucide-react';

export default function LiveDelegationChain({ executionResult, isRunning, activeChainId }) {
  const isBlocked = executionResult && (!executionResult.ok || executionResult.data?.status === "error" || executionResult.data?.decision === "DENY");
  const isAllowed = executionResult && executionResult.ok && (executionResult.data?.status === "completed" || executionResult.data?.authorization === "ALLOWED");
  const data = executionResult?.data || {};

  // Extract reasoning segments if present
  const reasoningRaw = data.llm_reasoning || "";
  let reasonA = "";
  let reasonB = "";
  let reasonC = "";

  if (reasoningRaw) {
    const parts = reasoningRaw.split(" | ");
    parts.forEach(p => {
      if (p.startsWith("Agent A:")) reasonA = p.replace("Agent A:", "").trim();
      else if (p.startsWith("Agent B:")) reasonB = p.replace("Agent B:", "").trim();
      else if (p.startsWith("Agent C:")) reasonC = p.replace("Agent C:", "").trim();
    });
  }

  const customerId = data.customer_id || (data.data?.customer_id) || "CUST-101";

  // Build the live nodes
  const nodes = [
    {
      id: "user",
      role: "Originating User",
      label: "USER-001",
      icon: User,
      scope: "Root Request",
      dataScope: [customerId],
      depth: 0,
      status: isRunning ? "RUNNING" : (executionResult ? "COMPLETED" : "WAITING"),
      reasoning: "Natural language financial analysis request dispatched."
    },
    {
      id: "agent_a",
      role: "Agent A (Coordinator)",
      label: "agent_a",
      icon: Bot,
      scope: "financials:read:all",
      dataScope: [customerId],
      depth: 0,
      status: isRunning ? "RUNNING" : (executionResult ? (isAllowed ? "COMPLETED" : (isBlocked && !data.data ? "BLOCKED" : "COMPLETED")) : "WAITING"),
      reasoning: reasonA || "Evaluates request, obtains server root token policy, and initiates chain delegation."
    },
    {
      id: "agent_b",
      role: "Agent B (Planner)",
      label: "agent_b",
      icon: Cpu,
      scope: "financials:read:summary",
      dataScope: [customerId],
      depth: 1,
      status: isRunning ? "RUNNING" : (isAllowed ? "COMPLETED" : (isBlocked ? "BLOCKED" : "WAITING")),
      reasoning: reasonB || "Decomposes analysis into bounded read scope and delegates child authority to Agent C."
    },
    {
      id: "agent_c",
      role: "Agent C (Worker)",
      label: "agent_c",
      icon: Bot,
      scope: data.operation ? `operation:${data.operation}` : "financials:read:summary",
      dataScope: [customerId],
      depth: 2,
      status: isRunning ? "RUNNING" : (isAllowed ? "COMPLETED" : (isBlocked ? "BLOCKED" : "WAITING")),
      reasoning: reasonC || "Selects governed tool operation and presents signed token to Governor PEP Gateway."
    },
    {
      id: "governor",
      role: "Delegation Governor",
      label: "PEP / PDP Gateway",
      icon: ShieldCheck,
      scope: "Monotonicity Validation",
      dataScope: ["Enforced"],
      depth: "PEP",
      status: isRunning ? "RUNNING" : (isAllowed ? "AUTHORIZED" : (isBlocked ? "REJECTED" : "WAITING")),
      reasoning: isAllowed 
        ? "Validated Ed25519 signature, audience, and customer boundary constraints." 
        : (isBlocked ? `Enforcement: ${data.message || data.error_code || "Access Denied"}` : "Policy Decision Point ready.")
    },
    {
      id: "financial_tool",
      role: "Financial Tool & DB",
      label: "MongoDB Atlas",
      icon: Database,
      scope: "Protected Financials",
      dataScope: [customerId],
      depth: "Tool",
      status: isRunning ? "RUNNING" : (isAllowed ? "READ COMPLETED" : (isBlocked ? "NOT EXECUTED" : "WAITING")),
      reasoning: isAllowed 
        ? `Customer document '${customerId}' read directly from MongoDB Atlas collection 'financial_records'.` 
        : (isBlocked ? "Protected database tool access was NOT executed." : "Awaiting Governor authorization.")
    }
  ];

  const getStatusBadge = (status) => {
    switch (status) {
      case "COMPLETED":
      case "AUTHORIZED":
      case "READ COMPLETED":
        return "bg-emerald-500/20 text-emerald-400 border-emerald-500/40";
      case "RUNNING":
        return "bg-sky-500/20 text-sky-400 border-sky-500/40 animate-pulse";
      case "BLOCKED":
      case "REJECTED":
      case "NOT EXECUTED":
        return "bg-rose-500/20 text-rose-400 border-rose-500/40";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Server className="w-5 h-5 text-emerald-400" />
              Live Multi-Agent Delegation Chain
            </h2>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              6 Hops Trace
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Real-time cryptographic token propagation across autonomous agents with monotonic scope enforcement
          </p>
        </div>

        {isRunning && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-sky-500/10 border border-sky-500/30 text-sky-400 text-xs font-mono font-semibold self-start sm:self-auto">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Multi-Agent Chain Executing...</span>
          </div>
        )}
      </div>

      {/* Grid of Nodes */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3.5 relative">
        {nodes.map((node, idx) => {
          const Icon = node.icon;
          const isLast = idx === nodes.length - 1;

          let cardStyle = "border-slate-800 bg-slate-900/60";
          if (node.status === "COMPLETED" || node.status === "AUTHORIZED" || node.status === "READ COMPLETED") {
            cardStyle = "border-emerald-500/40 bg-slate-900/90 shadow-md shadow-emerald-950/20";
          } else if (node.status === "BLOCKED" || node.status === "REJECTED" || node.status === "NOT EXECUTED") {
            cardStyle = "border-rose-500/40 bg-rose-950/20 shadow-md shadow-rose-950/20";
          } else if (node.status === "RUNNING") {
            cardStyle = "border-sky-500/50 bg-sky-950/20 shadow-md shadow-sky-950/20";
          }

          return (
            <div key={node.id} className="relative flex flex-col justify-between">
              <div className={`p-4 rounded-xl border transition-all duration-200 h-full flex flex-col justify-between ${cardStyle}`}>
                <div>
                  {/* Top: Icon & Depth */}
                  <div className="flex items-center justify-between gap-2 mb-2.5">
                    <div className="p-2 rounded-lg bg-slate-800 border border-slate-700 text-emerald-400">
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border bg-slate-950 text-slate-400 border-slate-800">
                      Depth: {node.depth}
                    </span>
                  </div>

                  {/* Role & Label */}
                  <div className="mb-2">
                    <h3 className="text-xs font-bold text-slate-200 truncate">{node.role}</h3>
                    <p className="text-[11px] font-mono text-sky-400">{node.label}</p>
                  </div>

                  {/* Scope & Data Scope */}
                  <div className="space-y-1.5 text-[10px] font-mono bg-slate-950/80 p-2 rounded-lg border border-slate-800/80 mb-2">
                    <div>
                      <span className="text-slate-500 block">Scope:</span>
                      <span className="text-emerald-300 truncate block font-medium">{node.scope}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Data Scope:</span>
                      <span className="text-amber-300 truncate block font-medium">
                        {Array.isArray(node.dataScope) ? node.dataScope.join(", ") : node.dataScope}
                      </span>
                    </div>
                  </div>

                  {/* Gemini Reasoning Tooltip/Snippet */}
                  {node.reasoning && (
                    <div className="text-[10px] text-slate-400 bg-slate-900/40 p-1.5 rounded border border-slate-800/50 leading-snug line-clamp-3">
                      {node.reasoning}
                    </div>
                  )}
                </div>

                {/* Bottom: Status Badge */}
                <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between">
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border font-bold ${getStatusBadge(node.status)}`}>
                    {node.status}
                  </span>
                  <KeyRound className="w-3.5 h-3.5 text-slate-500" />
                </div>
              </div>

              {/* Arrow Connector on Large Screens */}
              {!isLast && (
                <div className="hidden lg:flex absolute -right-3 top-1/2 -translate-y-1/2 z-10 p-1 rounded-full bg-slate-800 border border-slate-700 text-slate-400">
                  <ArrowRight className="w-3 h-3" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
