import React from 'react';
import { 
  Play, 
  ShieldAlert, 
  Flame, 
  Users, 
  FileWarning, 
  Clock, 
  UserX, 
  CheckCircle2, 
  Minimize2,
  Loader2
} from 'lucide-react';

export default function ScenarioRunner({ onRunScenario, isRunning, activeScenario }) {
  const scenarios = [
    {
      id: "normal_chain",
      title: "Run Normal 3-Agent Chain",
      description: "USER → Agent A → Agent B → Agent C → Governor → Financial Tool (CUST-101)",
      expected: "ALLOW",
      variant: "emerald",
      icon: Play,
      payload: {
        type: "agent_a",
        body: {
          task_type: "financial_analysis_task",
          originating_user: "USER-001",
          customer_id: "CUST-101",
          operation: "READ_SUMMARY"
        }
      }
    },
    {
      id: "agent_c_write",
      title: "Attempt Agent C Write",
      description: "Agent C presents read-only token attempting WRITE_RECORD at Governor Gateway",
      expected: "BLOCK (403)",
      variant: "rose",
      icon: ShieldAlert,
      payload: {
        type: "agent_c_write_attack",
        customer_id: "CUST-101"
      }
    },
    {
      id: "scope_escalation",
      title: "Attempt Scope Escalation",
      description: "Agent A (Read authority) attempts to delegate WRITE permission to Agent B",
      expected: "BLOCK (403)",
      variant: "rose",
      icon: Flame,
      payload: {
        type: "agent_a",
        body: {
          task_type: "financial_analysis_task",
          originating_user: "USER-001",
          customer_id: "CUST-101",
          operation: "READ_SUMMARY",
          simulate_attack: "escalate_write_to_b"
        }
      }
    },
    {
      id: "cross_customer",
      title: "Attempt Cross-Customer Access",
      description: "Token scoped strictly to CUST-101 presented to access CUST-102 records",
      expected: "BLOCK (403)",
      variant: "rose",
      icon: Users,
      payload: {
        type: "cross_customer_attack",
        allowed_customer: "CUST-101",
        target_customer: "CUST-102"
      }
    },
    {
      id: "tampered_token",
      title: "Test Tampered Token",
      description: "JWT token with corrupted cryptographic signature payload presented to Governor",
      expected: "BLOCK (401)",
      variant: "rose",
      icon: FileWarning,
      payload: {
        type: "tampered_jwt"
      }
    },
    {
      id: "expired_token",
      title: "Test Expired Token",
      description: "Delegation token presented after its expiration timestamp (TTL exceeded)",
      expected: "BLOCK (401)",
      variant: "amber",
      icon: Clock,
      payload: {
        type: "expired_token"
      }
    },
    {
      id: "wrong_audience",
      title: "Test Wrong Audience",
      description: "Token minted specifically for Agent B presented by Agent C",
      expected: "BLOCK (403)",
      variant: "rose",
      icon: UserX,
      payload: {
        type: "wrong_audience"
      }
    },
    {
      id: "verify_audit",
      title: "Verify Audit Ledger",
      description: "Recompute sequential SHA-256 hash chains across all transaction events in ledger",
      expected: "VALIDATE",
      variant: "sky",
      icon: CheckCircle2,
      payload: {
        type: "verify_ledger"
      }
    },
    {
      id: "scope_shrinkage",
      title: "Run Scope Shrinkage",
      description: "Monotonic scope reduction: A (read:all) → B (read:summary) → C (read:metrics)",
      expected: "ALLOW",
      variant: "emerald",
      icon: Minimize2,
      payload: {
        type: "scope_shrinkage"
      }
    }
  ];

  const getButtonStyles = (variant) => {
    switch (variant) {
      case "emerald":
        return "border-emerald-500/30 hover:border-emerald-500/60 bg-emerald-950/20 hover:bg-emerald-950/40 text-emerald-300";
      case "rose":
        return "border-rose-500/30 hover:border-rose-500/60 bg-rose-950/20 hover:bg-rose-950/40 text-rose-300";
      case "amber":
        return "border-amber-500/30 hover:border-amber-500/60 bg-amber-950/20 hover:bg-amber-950/40 text-amber-300";
      case "sky":
        return "border-sky-500/30 hover:border-sky-500/60 bg-sky-950/20 hover:bg-sky-950/40 text-sky-300";
      default:
        return "border-slate-700 bg-slate-800 text-slate-300";
    }
  };

  const getBadgeStyles = (expected) => {
    if (expected === "ALLOW") return "bg-emerald-500/20 text-emerald-400 border-emerald-500/40";
    if (expected.startsWith("BLOCK")) return "bg-rose-500/20 text-rose-400 border-rose-500/40";
    return "bg-sky-500/20 text-sky-400 border-sky-500/40";
  };

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Play className="w-4 h-4 text-emerald-400" />
            PS-2.3 Security Scenario Runner
          </h2>
          <p className="text-xs text-slate-400">
            Execute real automated governance verification scenarios against the live backend
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {scenarios.map((scenario) => {
          const Icon = scenario.icon;
          const isCurrent = isRunning && activeScenario === scenario.id;

          return (
            <button
              key={scenario.id}
              onClick={() => onRunScenario(scenario)}
              disabled={isRunning}
              className={`p-4 rounded-xl border text-left transition-all duration-200 flex flex-col justify-between group disabled:opacity-60 ${getButtonStyles(
                scenario.variant
              )} ${isCurrent ? 'ring-2 ring-emerald-400 scale-[0.99]' : 'hover:scale-[1.01]'}`}
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-lg bg-slate-900/80 border border-slate-800">
                      {isCurrent ? (
                        <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                      ) : (
                        <Icon className="w-4 h-4" />
                      )}
                    </div>
                    <span className="text-sm font-semibold text-slate-100 group-hover:text-white">
                      {scenario.title}
                    </span>
                  </div>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border font-semibold ${getBadgeStyles(scenario.expected)}`}>
                    {scenario.expected}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed line-clamp-2">
                  {scenario.description}
                </p>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                <span>Scenario ID: {scenario.id}</span>
                <span className="text-emerald-400 font-medium group-hover:underline">
                  {isCurrent ? "Executing..." : "Run Test →"}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
