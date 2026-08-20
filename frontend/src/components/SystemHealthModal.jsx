import React, { useState } from 'react';
import { X, Key, Shield, Server, Copy, Check } from 'lucide-react';

export default function SystemHealthModal({ isOpen, onClose, publicKey, policies, health }) {
  const [copiedKey, setCopiedKey] = useState(false);

  if (!isOpen) return null;

  const handleCopyKey = () => {
    if (publicKey?.public_key_pem) {
      navigator.clipboard.writeText(publicKey.public_key_pem);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="glass-panel w-full max-w-2xl rounded-2xl border border-slate-700 shadow-2xl p-6 relative max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
            <Key className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Governor Cryptographic Identity & Policies</h2>
            <p className="text-xs text-slate-400 font-mono">Ed25519 / EdDSA Asymmetric Key Infrastructure</p>
          </div>
        </div>

        {/* Public Key Section */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-300">Public Verification Key (PEM format)</span>
            <button
              onClick={handleCopyKey}
              className="flex items-center gap-1 text-[11px] font-mono text-slate-400 hover:text-emerald-400 transition-colors"
            >
              {copiedKey ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              {copiedKey ? "Copied" : "Copy PEM"}
            </button>
          </div>
          <pre className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-amber-300/90 overflow-x-auto whitespace-pre-wrap">
            {publicKey?.public_key_pem || "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAdDummyPublicKeyDataForDisplayOnly123456789=\n-----END PUBLIC KEY-----"}
          </pre>
          <div className="mt-2 text-[11px] font-mono text-slate-500">
            Algorithm: <span className="text-emerald-400">{publicKey?.algorithm || "Ed25519"}</span> • Issuer: <span className="text-sky-400">{publicKey?.issuer || "delegation-governor"}</span>
          </div>
        </div>

        {/* Server-Side Defined Root Authority Policies */}
        <div className="mb-6">
          <h3 className="text-xs font-semibold text-slate-300 mb-2">Registered Server-Side Authority Policies</h3>
          <p className="text-[11px] text-slate-400 mb-3">
            Clients cannot choose arbitrary root permissions. All delegations derive from pre-registered policy models:
          </p>
          <pre className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-sky-300 overflow-x-auto">
            {JSON.stringify(policies?.policies || {
              "financial_analysis_task": {
                "scopes": ["financials:read:all"],
                "resource": "customer_financials",
                "data_scope": { "customer_ids": ["CUST-101", "CUST-102", "CUST-103", "CUST-104", "CUST-105"] },
                "max_ttl": 300,
                "max_depth": 4
              },
              "single_customer_audit": {
                "scopes": ["financials:read:summary"],
                "resource": "customer_financials",
                "data_scope": { "customer_ids": ["CUST-101"] },
                "max_ttl": 180,
                "max_depth": 3
              }
            }, null, 2)}
          </pre>
        </div>

        <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-500/30 text-[11px] font-mono text-emerald-300 flex items-center gap-2">
          <Shield className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>Governor Private Signing Key is strictly isolated on the backend and never exposed through any endpoint.</span>
        </div>
      </div>
    </div>
  );
}
