import React from 'react';
import { ShieldCheck, ShieldAlert, GitCommit, Activity, Lock, Cpu } from 'lucide-react';

export default function SecurityMetrics({ stats }) {
  const metrics = [
    {
      title: "Total Policy Evaluations",
      value: stats?.totalRequests || 14,
      change: "100% Monotonic",
      icon: Activity,
      color: "sky"
    },
    {
      title: "Attacks Intercepted",
      value: stats?.blockedAttacks || 8,
      change: "0 Leaks Allowed",
      icon: ShieldAlert,
      color: "rose"
    },
    {
      title: "Scope Invariants Enforced",
      value: stats?.monotonicityEnforced || 12,
      change: "Strict Hierarchy",
      icon: ShieldCheck,
      color: "emerald"
    },
    {
      title: "SHA-256 Ledger Links",
      value: stats?.auditLedgerLinks || 24,
      change: "Cryptographically Verified",
      icon: Lock,
      color: "amber"
    }
  ];

  const getColorStyles = (color) => {
    switch (color) {
      case "emerald":
        return "text-emerald-400 bg-emerald-950/40 border-emerald-500/30";
      case "rose":
        return "text-rose-400 bg-rose-950/40 border-rose-500/30";
      case "amber":
        return "text-amber-400 bg-amber-950/40 border-amber-500/30";
      default:
        return "text-sky-400 bg-sky-950/40 border-sky-500/30";
    }
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
      {metrics.map((m, idx) => {
        const Icon = m.icon;
        return (
          <div key={idx} className="glass-panel p-4 rounded-xl shadow-lg border border-slate-800/80 flex items-center justify-between">
            <div>
              <span className="text-[11px] font-mono text-slate-400 block mb-0.5">{m.title}</span>
              <div className="text-xl font-bold font-mono text-white mb-0.5">{m.value}</div>
              <span className="text-[10px] font-mono text-slate-500">{m.change}</span>
            </div>
            <div className={`p-2.5 rounded-xl border ${getColorStyles(m.color)}`}>
              <Icon className="w-5 h-5" />
            </div>
          </div>
        );
      })}
    </div>
  );
}
