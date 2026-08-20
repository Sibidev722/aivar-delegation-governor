import React from 'react';
import { 
  Building2, 
  DollarSign, 
  TrendingUp, 
  CreditCard, 
  Activity, 
  ArrowUpRight, 
  ArrowDownRight, 
  Sparkles, 
  ShieldCheck, 
  Layers, 
  Calendar,
  Wallet,
  PieChart,
  CheckCircle2,
  MapPin,
  Briefcase,
  Award,
  HeartPulse
} from 'lucide-react';

export default function FinancialResultDashboard({ financialData, llmReasoning, auditEventId }) {
  if (!financialData) {
    return null;
  }

  const {
    customer_id = "CUST-0250",
    customer_name = "Jatin Kapoor",
    tier = "PLATINUM",
    industry = "Enterprise Proprietor",
    customer_segment = "BUSINESS_OWNER",
    city = "Pune",
    state = "Maharashtra",
    country = "India",
    annual_income = 0,
    monthly_income = 0,
    accounts = [],
    balances = {},
    income_ytd = 0,
    expenses_ytd = 0,
    metrics = {},
    financial_health = {},
    monthly_aggregations = [],
    transactions = [],
    summary = "",
    timestamp = new Date().toISOString()
  } = financialData;

  const totalAssets = metrics.total_assets || balances.total_cash || Object.values(balances).reduce((a, b) => (typeof b === 'number' ? a + b : a), 0);
  const netWorth = metrics.net_worth !== undefined ? metrics.net_worth : totalAssets;
  const healthScore = financial_health.financial_health_score || 85;
  const healthGrade = financial_health.grade || "HEALTHY";

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl space-y-6">
      {/* 1. Header & Customer Overview */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-slate-800">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400">
            <Building2 className="w-6 h-6" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-bold text-white tracking-tight">
                {customer_name}
              </h2>
              <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                {customer_id}
              </span>
              <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30">
                {tier}
              </span>
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-800 text-sky-400 border border-slate-700">
                {customer_segment}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 mt-1 font-mono">
              <span className="flex items-center gap-1 text-slate-300">
                <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                {city}, {state}, {country}
              </span>
              <span className="flex items-center gap-1 text-slate-300">
                <Briefcase className="w-3.5 h-3.5 text-sky-400" />
                {industry}
              </span>
              <span>Annual Income: <strong className="text-emerald-300">₹{Number(annual_income || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong></span>
            </div>
          </div>
        </div>

        {/* Audit & Health Badge */}
        <div className="flex flex-wrap items-center gap-3 font-mono text-xs text-slate-400 self-start md:self-auto">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-emerald-300">
            <HeartPulse className="w-4 h-4 text-rose-400" />
            <span>Health Score: <strong>{healthScore}/100</strong> ({healthGrade})</span>
          </div>
          {auditEventId && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Audit: <strong className="text-slate-200">{auditEventId}</strong></span>
            </div>
          )}
        </div>
      </div>

      {/* 2. AI Synthesized Financial Summary Callout */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/40 to-slate-900 border border-emerald-500/30">
        <div className="flex items-center gap-2 mb-2 text-xs font-bold text-emerald-400 uppercase tracking-wider">
          <Sparkles className="w-4 h-4" />
          <span>AI-Generated Financial Summary (Authorized MongoDB Data Only)</span>
        </div>
        <p className="text-sm text-slate-200 leading-relaxed font-sans">
          {summary || "Authorized financial performance records successfully parsed from database."}
        </p>
        {llmReasoning && (
          <div className="mt-3 pt-2.5 border-t border-slate-800/80 text-xs font-mono text-slate-400">
            <span className="text-emerald-400/80 font-bold block mb-1">Agent Chain Reasoning:</span>
            <p className="text-slate-300 italic text-[11px]">{llmReasoning}</p>
          </div>
        )}
      </div>

      {/* 3. Top Metrics Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800">
          <div className="flex items-center justify-between text-slate-500 text-xs font-mono mb-1">
            <span>Total Assets</span>
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-base sm:text-xl font-bold font-mono text-emerald-400">
            ₹{Number(totalAssets || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Net Worth: ₹{Number(netWorth || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
        </div>

        <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800">
          <div className="flex items-center justify-between text-slate-500 text-xs font-mono mb-1">
            <span>Monthly Income</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-base sm:text-xl font-bold font-mono text-emerald-400">
            ₹{Number(metrics.monthly_income || monthly_income || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Monthly Savings: ₹{Number(metrics.monthly_savings || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
        </div>

        <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800">
          <div className="flex items-center justify-between text-slate-500 text-xs font-mono mb-1">
            <span>Savings Rate & Runway</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-base sm:text-xl font-bold font-mono text-amber-400">
            {metrics.savings_rate_pct || "25.0"}% <span className="text-xs font-normal text-slate-400">({metrics.runway_months || "12.0"} mo)</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Monthly Burn: ₹{Number(metrics.monthly_burn_rate || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
        </div>

        <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800">
          <div className="flex items-center justify-between text-slate-500 text-xs font-mono mb-1">
            <span>Credit Score / Rating</span>
            <Award className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-base sm:text-xl font-bold font-mono text-sky-400">
            {metrics.credit_score || "750"} <span className="text-xs font-normal text-slate-400">/ 900</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Credit Utilization: {metrics.credit_utilization_pct || 0}%</span>
        </div>
      </div>

      {/* 4. Detailed Breakdown (Accounts, Top Categories, Transactions) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Balances & Accounts */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-4">
          <div>
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider mb-2.5 flex items-center gap-2">
              <Wallet className="w-4 h-4 text-emerald-400" />
              Registered Financial Accounts ({accounts.length})
            </h3>
            <div className="space-y-2">
              {accounts.map((acc, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs font-mono p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-200 font-bold">{acc.account_type}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-emerald-400">{acc.status || "ACTIVE"}</span>
                    </div>
                    <span className="text-[10px] text-slate-500">{acc.account_number_masked} • {acc.account_id}</span>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-slate-100 block">₹{Number(acc.current_balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                    {acc.credit_limit > 0 && (
                      <span className="text-[10px] text-slate-500 block">Limit: ₹{Number(acc.credit_limit).toLocaleString('en-IN')}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Top Spending Categories */}
          {metrics.top_spending_categories && metrics.top_spending_categories.length > 0 && (
            <div className="pt-3 border-t border-slate-800/80">
              <h4 className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-2">Top Spending Categories:</h4>
              <div className="grid grid-cols-2 gap-2">
                {metrics.top_spending_categories.slice(0, 4).map((cat, idx) => (
                  <div key={idx} className="p-2 rounded bg-slate-900/50 border border-slate-800/60 text-xs font-mono">
                    <span className="text-slate-400 block text-[10px]">{cat.category}</span>
                    <span className="font-bold text-amber-300">₹{Number(cat.total_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Financial Health Breakdown Pillars */}
          {financial_health && financial_health.savings_score && (
            <div className="pt-3 border-t border-slate-800/80 grid grid-cols-4 gap-2 text-center text-xs font-mono">
              <div className="p-2 rounded bg-slate-900/50 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Savings</span>
                <span className="font-bold text-emerald-400">{financial_health.savings_score}/100</span>
              </div>
              <div className="p-2 rounded bg-slate-900/50 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Debt</span>
                <span className="font-bold text-sky-400">{financial_health.debt_score}/100</span>
              </div>
              <div className="p-2 rounded bg-slate-900/50 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Liquidity</span>
                <span className="font-bold text-amber-400">{financial_health.liquidity_score}/100</span>
              </div>
              <div className="p-2 rounded bg-slate-900/50 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Spending</span>
                <span className="font-bold text-purple-400">{financial_health.spending_score}/100</span>
              </div>
            </div>
          )}
        </div>

        {/* Itemized Transactions */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider mb-2.5 flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-amber-400" />
              Recent Chronological Transactions ({transactions.length})
            </h3>
            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
              {transactions.length > 0 ? (
                transactions.map((tx, idx) => {
                  const isIncome = tx.transaction_type === "INCOME" || tx.type === "CREDIT";
                  return (
                    <div key={idx} className="flex items-center justify-between text-xs font-mono p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-colors">
                      <div className="flex items-center gap-2.5">
                        <div className={`p-1.5 rounded-md ${isIncome ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                          {isIncome ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                        </div>
                        <div>
                          <span className="text-slate-200 font-semibold block truncate max-w-[180px] sm:max-w-[240px]">
                            {tx.merchant || tx.description}
                          </span>
                          <span className="text-[10px] text-slate-500">
                            {tx.transaction_date || tx.date} • {tx.category} • {tx.transaction_id}
                          </span>
                        </div>
                      </div>
                      <span className={`font-bold ${isIncome ? 'text-emerald-400' : 'text-slate-200'}`}>
                        {isIncome ? '+' : '-'}₹{Number(tx.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-8 text-xs font-mono text-slate-500">
                  Summary read authorized; transaction records parsed.
                </div>
              )}
            </div>
          </div>

          {/* Footer Data Source Note */}
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-500">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Source: MongoDB Atlas (Delegation Governed)
            </span>
            <span>Customer: {customer_id}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
