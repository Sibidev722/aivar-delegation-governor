import React, { useState } from 'react';
import { 
  FileText, 
  CheckCircle2, 
  XCircle, 
  ShieldCheck, 
  Link2, 
  Search, 
  Lock, 
  AlertTriangle,
  Loader2
} from 'lucide-react';
import { verifyAuditChain } from '../services/api';

export default function AuditLedgerView({ auditEvents, activeChainId }) {
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [filterText, setFilterText] = useState("");

  const handleVerify = async () => {
    if (!activeChainId) return;
    setVerifying(true);
    setVerificationResult(null);
    try {
      const res = await verifyAuditChain(activeChainId);
      if (res.ok) {
        setVerificationResult(res.data);
      } else {
        setVerificationResult({ valid: false, tampered: true, reason: res.data?.detail || "Verification failed" });
      }
    } catch (err) {
      setVerificationResult({ valid: false, tampered: true, reason: err.message });
    } finally {
      setVerifying(false);
    }
  };

  // Mock / default audit events if none present
  const displayEvents = auditEvents && auditEvents.length > 0 ? auditEvents : [
    {
      sequence: 0,
      timestamp: new Date().toISOString(),
      chain_id: activeChainId || "urn:uuid:sample-chain-01",
      event_type: "TOKEN_MINTED",
      actor: "USER-001",
      target: "agent_a",
      decision: "ALLOW",
      reason: "Minted root token under server policy 'financial_analysis_task'",
      previous_event_hash: "0000000000000000000000000000000000000000000000000000000000000000",
      event_hash: "9b1deb4d3b7d4bad9bdd2b0d7b3dcb6de3b0c44298fc1c149afbf4c8996fb924"
    },
    {
      sequence: 1,
      timestamp: new Date().toISOString(),
      chain_id: activeChainId || "urn:uuid:sample-chain-01",
      event_type: "DELEGATION_ALLOWED",
      actor: "agent_a",
      target: "agent_b",
      decision: "ALLOW",
      reason: "Delegation passed all scope and data monotonicity checks",
      previous_event_hash: "9b1deb4d3b7d4bad9bdd2b0d7b3dcb6de3b0c44298fc1c149afbf4c8996fb924",
      event_hash: "8f4a9cc197ce098040b28a9bd4b94a3e7391c82c35d9d0b3699cf429ff9"
    }
  ];

  const filteredEvents = displayEvents.filter((e) => {
    const search = filterText.toLowerCase();
    return (
      e.event_type.toLowerCase().includes(search) ||
      e.actor.toLowerCase().includes(search) ||
      e.target.toLowerCase().includes(search) ||
      e.reason.toLowerCase().includes(search)
    );
  });

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Lock className="w-4 h-4 text-emerald-400" />
              Tamper-Evident Hash-Chained Audit Ledger
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              SHA-256 Sequential Links
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Cryptographically linked immutable log entries with backward hash pointers
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Search Filter */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Filter events..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          {/* Verify Hash Chain Button */}
          <button
            onClick={handleVerify}
            disabled={verifying}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/20 transition-colors disabled:opacity-50"
          >
            {verifying ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <ShieldCheck className="w-3.5 h-3.5" />
            )}
            <span>Verify Ledger Integrity</span>
          </button>
        </div>
      </div>

      {/* Verification Result Banner */}
      {verificationResult && (
        <div className={`mb-4 p-3.5 rounded-xl border text-xs font-mono flex items-start gap-2.5 ${
          verificationResult.valid 
            ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300' 
            : 'bg-rose-950/30 border-rose-500/40 text-rose-300'
        }`}>
          {verificationResult.valid ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          )}
          <div>
            <div className="font-bold mb-0.5">
              {verificationResult.valid 
                ? `LEDGER INTEGRITY VERIFIED: All ${verificationResult.total_events || 0} hash links mathematically valid.` 
                : `TAMPERING DETECTED at sequence index ${verificationResult.broken_link_index ?? 'unknown'}`}
            </div>
            <p className="text-[11px] opacity-90">
              {verificationResult.reason || "All SHA-256 canonical event hashes and backward pointers match perfectly."}
            </p>
          </div>
        </div>
      )}

      {/* Event Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-slate-900/90 text-slate-400 text-[11px] uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="py-3 px-4">Seq</th>
              <th className="py-3 px-4">Event Type</th>
              <th className="py-3 px-4">Actor → Target</th>
              <th className="py-3 px-4">Decision</th>
              <th className="py-3 px-4">Reason</th>
              <th className="py-3 px-4">Event Hash Link</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {filteredEvents.map((evt, idx) => {
              const isAllow = evt.decision === "ALLOW";

              return (
                <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                  <td className="py-3 px-4 text-slate-500 font-bold">#{evt.sequence}</td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700 text-[11px]">
                      {evt.event_type}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="text-sky-400">{evt.actor}</span>
                    <span className="text-slate-500 mx-1.5">→</span>
                    <span className="text-amber-400">{evt.target}</span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                      isAllow 
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                        : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                    }`}>
                      {evt.decision}
                    </span>
                  </td>
                  <td className="py-3 px-4 max-w-[280px] truncate text-slate-300" title={evt.reason}>
                    {evt.reason}
                  </td>
                  <td className="py-3 px-4 text-[11px] text-slate-400">
                    <div className="flex items-center gap-1.5" title={`Hash: ${evt.event_hash}\nPrev: ${evt.previous_event_hash}`}>
                      <Link2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span className="truncate max-w-[100px] text-slate-400">{evt.event_hash}</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
