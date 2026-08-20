import React from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  Database, 
  Lock, 
  Key, 
  FileCode, 
  Cpu, 
  Layers,
  Copy,
  Check
} from 'lucide-react';

export default function SecurityPanel({ executionResult, isRunning }) {
  const [copied, setCopied] = React.useState(false);

  const handleCopyChainId = (chainId) => {
    if (!chainId) return;
    navigator.clipboard.writeText(chainId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!executionResult && !isRunning) {
    return (
      <div className="glass-panel rounded-2xl p-5 shadow-xl">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-white">Security & Authorization Gateway</h3>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
            Awaiting Request
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Every financial query must pass cryptographic Ed25519 signature checks, audience binding, and monotonic customer data scope evaluation before reaching MongoDB.
        </p>
      </div>
    );
  }

  const isSuccess = executionResult?.ok && (executionResult?.data?.status === "completed" || executionResult?.data?.authorization === "ALLOWED");
  const isBlocked = executionResult && !isSuccess;
  const data = executionResult?.data || {};

  const customerId = data.customer_id || (data.details?.target_customer) || (data.data?.customer_id) || "CUST-101";
  const operation = data.operation || (data.details?.operation) || "READ_SUMMARY";
  const scope = (data.details?.required_scope) || (data.details?.requested_scopes?.[0]) || (operation === "READ_SUMMARY" ? "financials:read:summary" : operation === "READ_METRICS" ? "financials:read:metrics" : "financials:read:all");
  const reason = data.message || data.error_code || (isSuccess ? "Monotonic scope verified and authorized" : "Access denied by Central Governor");
  const errorCode = data.error_code || (isBlocked ? "AUTHORIZATION_REJECTED" : null);

  return (
    <div className={`rounded-2xl p-5 shadow-xl border transition-all duration-200 ${
      isSuccess 
        ? 'glass-panel-glow-emerald' 
        : isBlocked 
        ? 'glass-panel-glow-rose' 
        : 'glass-panel'
    }`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className={`p-2 rounded-xl border ${
            isSuccess 
              ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' 
              : isBlocked 
              ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' 
              : 'bg-sky-500/20 text-sky-400 border-sky-500/30'
          }`}>
            {isSuccess ? <ShieldCheck className="w-5 h-5" /> : isBlocked ? <ShieldAlert className="w-5 h-5" /> : <Cpu className="w-5 h-5 animate-pulse" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white">Governor Security Verification</h3>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border font-bold ${
                isSuccess 
                  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' 
                  : isBlocked 
                  ? 'bg-rose-500/20 text-rose-400 border-rose-500/40' 
                  : 'bg-sky-500/20 text-sky-400 border-sky-500/40'
              }`}>
                {isRunning ? "EVALUATING..." : isSuccess ? "AUTHORIZED" : "REQUEST BLOCKED"}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">
              {isRunning 
                ? "Checking Ed25519 token signatures & policy monotonicity..." 
                : isSuccess 
                ? `Passed all Governor Policy Enforcement Point (PEP) validations`
                : `Blocked by Governor PEP (${errorCode})`}
            </p>
          </div>
        </div>

        {/* Chain ID Pill */}
        {data.chain_id && (
          <button
            onClick={() => handleCopyChainId(data.chain_id)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-300 hover:border-slate-700 transition-colors self-start sm:self-auto"
            title="Click to copy Chain ID"
          >
            <span className="text-slate-500">Chain:</span>
            <span className="text-sky-400 truncate max-w-[120px]">{data.chain_id}</span>
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-slate-500" />}
          </button>
        )}
      </div>

      {/* Grid of Security Parameters */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 mb-4">
        {/* Authorization */}
        <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800">
          <span className="text-[10px] text-slate-500 font-mono block mb-1">Authorization</span>
          <span className={`text-xs font-mono font-bold flex items-center gap-1 ${
            isSuccess ? 'text-emerald-400' : isBlocked ? 'text-rose-400' : 'text-sky-400'
          }`}>
            {isSuccess ? <CheckCircle2 className="w-3.5 h-3.5" /> : isBlocked ? <XCircle className="w-3.5 h-3.5" /> : <Cpu className="w-3.5 h-3.5" />}
            {isSuccess ? "AUTHORIZED" : isBlocked ? "BLOCKED" : "CHECKING"}
          </span>
        </div>

        {/* Operation */}
        <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800">
          <span className="text-[10px] text-slate-500 font-mono block mb-1">Operation</span>
          <span className="text-xs font-mono font-bold text-slate-200 truncate block">
            {operation}
          </span>
        </div>

        {/* Customer Scope */}
        <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800">
          <span className="text-[10px] text-slate-500 font-mono block mb-1">Target Customer</span>
          <span className="text-xs font-mono font-bold text-amber-300 truncate block">
            {customerId}
          </span>
        </div>

        {/* Granted Scope */}
        <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800">
          <span className="text-[10px] text-slate-500 font-mono block mb-1">Required Scope</span>
          <span className="text-xs font-mono font-medium text-emerald-300 truncate block">
            {scope}
          </span>
        </div>

        {/* Governor PDP Check */}
        <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800">
          <span className="text-[10px] text-slate-500 font-mono block mb-1">Governor PDP</span>
          <span className={`text-xs font-mono font-bold ${
            isSuccess ? 'text-emerald-400' : isBlocked ? 'text-rose-400' : 'text-slate-400'
          }`}>
            {isSuccess ? "PASSED" : isBlocked ? "DENIED" : "..."}
          </span>
        </div>

        {/* Financial Tool Execution */}
        <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800">
          <span className="text-[10px] text-slate-500 font-mono block mb-1">Financial Tool</span>
          <span className={`text-xs font-mono font-bold ${
            isSuccess ? 'text-emerald-400' : isBlocked ? 'text-rose-400' : 'text-slate-400'
          }`}>
            {isSuccess ? "EXECUTED" : isBlocked ? "NOT EXECUTED" : "..."}
          </span>
        </div>
      </div>

      {/* Rejection / Success Details Bar */}
      {isBlocked && (
        <div className="p-3.5 rounded-xl bg-rose-950/30 border border-rose-500/40 text-xs font-mono text-rose-300 space-y-1">
          <div className="flex items-center gap-1.5 font-bold text-rose-200">
            <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>SECURITY REASON: {errorCode || "ACCESS_DENIED"}</span>
          </div>
          <p className="text-rose-300/90 pl-5 text-[11px] leading-relaxed">{reason}</p>
          <div className="pl-5 pt-1 text-[11px] text-slate-400 flex items-center gap-4">
            <span>Financial Tool: <strong className="text-rose-400">NOT EXECUTED</strong></span>
            <span>MongoDB Data: <strong className="text-rose-400">UNTOUCHED</strong></span>
          </div>
        </div>
      )}

      {isSuccess && data.audit_event_id && (
        <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-500/30 text-xs font-mono text-emerald-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Audit Recorded: <strong className="text-white">{data.audit_event_id}</strong></span>
          </div>
          <span className="text-[11px] text-slate-400">Tamper-evident SHA-256 sealed</span>
        </div>
      )}
    </div>
  );
}
