import React, { useState } from 'react';
import { Sparkles, ArrowRight, Loader2, Bot, ShieldCheck, Terminal, HelpCircle } from 'lucide-react';

export default function NaturalLanguageInput({ onSubmit, isRunning, defaultPrompt = "" }) {
  const [prompt, setPrompt] = useState(defaultPrompt || "Read and summarize CUST-0250");

  const examplePrompts = [
    "Read and summarize CUST-0250",
    "Show the financial metrics for CUST-0001",
    "Analyze the financial performance of CUST-0100",
    "Read financial balances and transactions for CUST-0350",
    "Summarize financial health of CUST-0500"
  ];

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!prompt.trim() || isRunning) return;
    onSubmit(prompt.trim());
  };

  const handleChipClick = (example) => {
    setPrompt(example);
    if (!isRunning) {
      onSubmit(example);
    }
  };

  return (
    <div className="glass-panel-glow-emerald rounded-2xl p-6 shadow-2xl relative overflow-hidden">
      {/* Background Accent Graphic */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

      <div className="relative z-10">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">
                Ask the Financial Agents
              </h2>
              <p className="text-xs text-slate-400">
                Natural-language queries autonomously routed across 500 customers (CUST-0001 to CUST-0500) and verified by Central Governor PEP
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-slate-400 bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-800 self-start sm:self-auto">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Zero Trust • 500 Customers Pool</span>
          </div>
        </div>

        {/* Search / Prompt Form */}
        <form onSubmit={handleSubmit} className="mb-4">
          <div className="relative flex items-center">
            <div className="absolute left-4 text-slate-400">
              <Terminal className="w-5 h-5 text-emerald-400" />
            </div>
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={isRunning}
              placeholder="e.g. Read and summarize CUST-0250"
              className="w-full bg-slate-950/90 border-2 border-slate-700/80 focus:border-emerald-500/80 rounded-xl pl-12 pr-40 py-3.5 text-sm md:text-base text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 transition-all font-sans disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={isRunning || !prompt.trim()}
              className="absolute right-2 px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white text-xs md:text-sm font-semibold rounded-lg flex items-center gap-2 shadow-lg shadow-emerald-950/50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98]"
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <span>Run Analysis</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>

        {/* Quick Example Prompt Chips */}
        <div>
          <div className="flex items-center gap-2 mb-2 text-xs font-mono text-slate-400">
            <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
            <span>Try sample requests from 500-customer dataset:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {examplePrompts.map((example, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleChipClick(example)}
                disabled={isRunning}
                className="text-xs font-mono px-3 py-1.5 rounded-lg bg-slate-900/90 hover:bg-slate-800 text-slate-300 hover:text-emerald-300 border border-slate-800 hover:border-emerald-500/40 transition-all duration-150 disabled:opacity-50 text-left"
              >
                "{example}"
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
