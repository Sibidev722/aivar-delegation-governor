import React from 'react';
import { Shield, Key, Database, Activity, RefreshCw } from 'lucide-react';

export default function Header({ health, isRefreshing, onRefresh, onOpenKeyModal, activeChainId }) {
  const isHealthy = health?.status === "healthy" || health?.status === "ok";

  return (
    <header className="border-b border-cyber-border bg-cyber-slate/90 backdrop-blur-md sticky top-0 z-40 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Left: Brand / Title */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 text-white shadow-lg shadow-emerald-500/20">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white">
                Delegation Chain Governor
              </h1>
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                PS-2.3 Spec
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Asymmetric Ed25519 Multi-Agent Policy Decision & Enforcement Layer
            </p>
          </div>
        </div>

        {/* Right: Status Indicators & Quick Actions */}
        <div className="flex items-center gap-3">
          {/* Active Chain Pill */}
          {activeChainId && (
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 text-xs font-mono text-slate-300">
              <span className="text-slate-500">Chain:</span>
              <span className="text-sky-400 truncate max-w-[140px]">{activeChainId}</span>
            </div>
          )}

          {/* Backend Health Badge */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700">
            <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
            <span className="text-xs font-medium text-slate-300">
              {isHealthy ? "Governor Active" : "Governor Offline"}
            </span>
          </div>

          {/* Ed25519 Public Key Modal Trigger */}
          <button
            onClick={onOpenKeyModal}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700 transition-colors"
            title="Inspect Ed25519 Public Key"
          >
            <Key className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden md:inline">Public Key</span>
          </button>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors disabled:opacity-50"
            title="Refresh Ledger & Status"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
}
