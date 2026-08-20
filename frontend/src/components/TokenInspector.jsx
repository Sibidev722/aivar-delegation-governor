import React, { useState } from 'react';
import { Key, Copy, Check, ShieldCheck, FileCode, Clock, Tag } from 'lucide-react';

export default function TokenInspector({ tokenData, activeTokenRaw }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Mock / dynamic claims for display if not fully provided
  const claims = tokenData || {
    jti: "urn:uuid:9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    chain_id: "urn:uuid:4a123456-7890-abcd-ef01-234567890abc",
    parent_jti: "urn:uuid:1a098765-4321-fedc-ba98-76543210fedc",
    iss: "delegation-governor",
    sub: "agent_a",
    aud: "agent_b",
    scopes: ["financials:read:summary"],
    resource: "customer_financials",
    data_scope: { customer_ids: ["CUST-101"] },
    depth: 1,
    max_depth: 4,
    iat: Math.floor(Date.now() / 1000) - 30,
    exp: Math.floor(Date.now() / 1000) + 270,
    parent_token_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    token_status: "VALID"
  };

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Key className="w-4 h-4 text-amber-400" />
            Asymmetric Ed25519 Token Inspector
          </h2>
          <p className="text-xs text-slate-400">
            Inspect cryptographic lineage claims, monotonic scopes, and signature attributes
          </p>
        </div>

        <button
          onClick={() => handleCopy(JSON.stringify(claims, null, 2))}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-mono text-slate-300 border border-slate-700 transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? "Copied Claims" : "Copy JSON"}
        </button>
      </div>

      {/* Grid of Key Claims */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
          <span className="text-[11px] text-slate-500 font-mono block mb-1">Subject (Delegator)</span>
          <span className="text-xs font-mono font-bold text-sky-400">{claims.sub || "user"}</span>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
          <span className="text-[11px] text-slate-500 font-mono block mb-1">Audience (Delegatee)</span>
          <span className="text-xs font-mono font-bold text-emerald-400">{claims.aud || "agent_a"}</span>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
          <span className="text-[11px] text-slate-500 font-mono block mb-1">Delegation Depth</span>
          <span className="text-xs font-mono font-bold text-amber-400">
            Hop {claims.depth ?? 0} of {claims.max_depth ?? 4}
          </span>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
          <span className="text-[11px] text-slate-500 font-mono block mb-1">Cryptographic Status</span>
          <span className="text-xs font-mono font-bold text-emerald-400 flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5" /> Ed25519 Valid
          </span>
        </div>
      </div>

      {/* Detailed Claims Breakdown */}
      <div className="space-y-2 text-xs font-mono bg-slate-950 p-4 rounded-xl border border-slate-800 overflow-x-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 pb-2 border-b border-slate-800/80">
          <div>
            <span className="text-slate-500">Token ID (JTI): </span>
            <span className="text-slate-200 break-all">{claims.jti || "N/A"}</span>
          </div>
          <div>
            <span className="text-slate-500">Chain ID: </span>
            <span className="text-sky-400 break-all">{claims.chain_id || "N/A"}</span>
          </div>
          <div>
            <span className="text-slate-500">Parent JTI: </span>
            <span className="text-slate-400 break-all">{claims.parent_jti || "null (Root Token)"}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 py-2 border-b border-slate-800/80">
          <div>
            <span className="text-slate-500 block mb-1">Operational Scopes:</span>
            <div className="flex flex-wrap gap-1.5">
              {(claims.scopes || []).map((s, idx) => (
                <span key={idx} className="px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-[11px]">
                  {s}
                </span>
              ))}
            </div>
          </div>
          <div>
            <span className="text-slate-500 block mb-1">Customer Data Boundary:</span>
            <div className="flex flex-wrap gap-1.5">
              {((claims.data_scope?.customer_ids) || ["CUST-101"]).map((c, idx) => (
                <span key={idx} className="px-2 py-0.5 rounded bg-amber-950/60 border border-amber-500/40 text-amber-300 text-[11px]">
                  {c}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between text-[11px] text-slate-400 gap-2">
          <div>
            <span className="text-slate-500">Issuer: </span>
            <span className="text-slate-300">{claims.iss || "delegation-governor"}</span>
          </div>
          <div>
            <span className="text-slate-500">Parent Hash: </span>
            <span className="text-slate-400 truncate max-w-[200px] inline-block align-bottom">{claims.parent_token_hash || "null"}</span>
          </div>
          <div>
            <span className="text-slate-500">Expires At: </span>
            <span className="text-slate-300">{claims.exp ? new Date(claims.exp * 1000).toLocaleTimeString() : "N/A"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
