import React, { useState } from 'react';
import { Database, DollarSign, TrendingUp, CreditCard, Activity, ArrowUpRight, ArrowDownRight, Search, MapPin, Briefcase } from 'lucide-react';

const FEATURED_CUSTOMERS = [
  {
    customer_id: "CUST-0250",
    customer_name: "Jatin Kapoor",
    tier: "PLATINUM",
    customer_segment: "BUSINESS_OWNER",
    city: "Pune",
    state: "Maharashtra",
    industry: "Enterprise Proprietor",
    annual_income: 7800000.0,
    monthly_income: 650000.0,
    balances: { savings: 1425000.0, investment: 5500000.0, total_cash: 6925000.0 },
    transactions: [
      { transaction_id: "TX-0250-0001", date: "2026-08-01", amount: 650000.0, type: "CREDIT", category: "BUSINESS_REVENUE", merchant: "Corporate Direct Invoicing", description: "Enterprise logistics contract monthly settlement" },
      { transaction_id: "TX-0250-0002", date: "2026-08-05", amount: 185000.0, type: "DEBIT", category: "RENT", merchant: "Residential Society Lease Escrow", description: "Commercial & residential office lease" }
    ],
    metrics: { monthly_burn_rate: 285000.0, runway_months: 24.3, credit_score: 840, savings_rate_pct: 56.2 },
    summary: "High net-worth business owner with substantial investment assets and 24.3 months of liquidity runway."
  },
  {
    customer_id: "CUST-0001",
    customer_name: "Aarav Sharma",
    tier: "PREMIUM",
    customer_segment: "SALARIED",
    city: "Bengaluru",
    state: "Karnataka",
    industry: "Software Engineer",
    annual_income: 1800000.0,
    monthly_income: 150000.0,
    balances: { savings: 380000.0, investment: 850000.0, total_cash: 1230000.0 },
    transactions: [
      { transaction_id: "TX-0001-0001", date: "2026-08-01", amount: 150000.0, type: "CREDIT", category: "SALARY", merchant: "Tech Systems Monthly Wage", description: "Monthly Engineering Payroll" }
    ],
    metrics: { monthly_burn_rate: 75000.0, runway_months: 16.4, credit_score: 790, savings_rate_pct: 50.0 },
    summary: "Senior software engineer with stable tech payroll cashflow and strong monthly savings."
  },
  {
    customer_id: "CUST-0100",
    customer_name: "Pooja Verma",
    tier: "GOLD",
    customer_segment: "PROFESSIONAL",
    city: "Mumbai",
    state: "Maharashtra",
    industry: "Chartered Accountant",
    annual_income: 3200000.0,
    monthly_income: 266666.67,
    balances: { checking: 650000.0, investment: 2100000.0, total_cash: 2750000.0 },
    transactions: [
      { transaction_id: "TX-0100-0001", date: "2026-08-02", amount: 266000.0, type: "CREDIT", category: "CONSULTING_FEE", merchant: "Corporate Direct Payroll", description: "Audit & Advisory Retainer Fee" }
    ],
    metrics: { monthly_burn_rate: 110000.0, runway_months: 25.0, credit_score: 830, savings_rate_pct: 58.7 },
    summary: "Licensed financial professional in Mumbai with strong investment reserves."
  },
  {
    customer_id: "CUST-0350",
    customer_name: "Rajesh Iyer",
    tier: "STANDARD",
    customer_segment: "RETIRED",
    city: "Chennai",
    state: "Tamil Nadu",
    industry: "Retired Bank Executive",
    annual_income: 750000.0,
    monthly_income: 62500.0,
    balances: { savings: 480000.0, investment: 1200000.0, total_cash: 1680000.0 },
    transactions: [
      { transaction_id: "TX-0350-0001", date: "2026-08-01", amount: 62500.0, type: "CREDIT", category: "PENSION", merchant: "Corporate Direct Payroll", description: "Monthly Pension Settlement" }
    ],
    metrics: { monthly_burn_rate: 38000.0, runway_months: 44.2, credit_score: 810, savings_rate_pct: 39.2 },
    summary: "Retired banking executive with conservative risk profile and high liquidity."
  },
  {
    customer_id: "CUST-0500",
    customer_name: "Tanvi Patel",
    tier: "STANDARD",
    customer_segment: "STUDENT",
    city: "Ahmedabad",
    state: "Gujarat",
    industry: "Graduate Research Scholar",
    annual_income: 180000.0,
    monthly_income: 15000.0,
    balances: { savings: 42000.0, total_cash: 42000.0 },
    transactions: [
      { transaction_id: "TX-0500-0001", date: "2026-08-01", amount: 15000.0, type: "CREDIT", category: "SCHOLARSHIP", merchant: "Corporate Direct Payroll", description: "Monthly Research Stipend" }
    ],
    metrics: { monthly_burn_rate: 11500.0, runway_months: 3.6, credit_score: 680, savings_rate_pct: 23.3 },
    summary: "University research scholar with modest living expenses and disciplined student stipend budget."
  }
];

export default function CustomerDataViewer({ liveCustomerData }) {
  const [selectedCustomerId, setSelectedCustomerId] = useState("CUST-0250");
  const [customSearchId, setCustomSearchId] = useState("");

  const customer = (liveCustomerData && liveCustomerData.customer_id === selectedCustomerId)
    ? { ...FEATURED_CUSTOMERS.find(c => c.customer_id === selectedCustomerId), ...liveCustomerData }
    : FEATURED_CUSTOMERS.find(c => c.customer_id === selectedCustomerId) || FEATURED_CUSTOMERS[0];

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Database className="w-4 h-4 text-sky-400" />
            Protected Financial Records Pool (500 Customers)
          </h2>
          <p className="text-xs text-slate-400">
            Preview isolated customer records (CUST-0001 to CUST-0500) governed strictly through Policy Enforcement Points
          </p>
        </div>

        {/* Customer Selector Tabs */}
        <div className="flex flex-wrap gap-1.5 p-1 rounded-xl bg-slate-900 border border-slate-800">
          {FEATURED_CUSTOMERS.map((c) => (
            <button
              key={c.customer_id}
              onClick={() => setSelectedCustomerId(c.customer_id)}
              className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition-colors ${
                selectedCustomerId === c.customer_id
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {c.customer_id}
            </button>
          ))}
        </div>
      </div>

      {/* Overview Banner */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <h3 className="text-sm font-bold text-white">{customer.customer_name}</h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              {customer.customer_id}
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-sky-400 border border-slate-700">
              {customer.tier} • {customer.customer_segment}
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs text-slate-400 font-mono">
            <span>Location: {customer.city}, {customer.state}</span>
            <span>Occupation: {customer.industry}</span>
          </div>
        </div>

        <div className="flex items-center gap-6 font-mono">
          <div>
            <span className="text-[10px] text-slate-500 block">Total Assets</span>
            <span className="text-sm font-bold text-emerald-400">
              ₹{(customer.balances?.total_cash || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 block">Runway</span>
            <span className="text-sm font-bold text-amber-400">
              {customer.metrics?.runway_months || "N/A"} mo
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 block">Credit Score</span>
            <span className="text-sm font-bold text-sky-400">
              {customer.metrics?.credit_score || "N/A"}
            </span>
          </div>
        </div>
      </div>

      {/* Balances & Transactions Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Balances Breakdown */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <h4 className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
            Account Balances Breakdown
          </h4>
          <div className="space-y-2">
            {Object.entries(customer.balances || {}).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between text-xs font-mono py-1.5 px-2 rounded-lg bg-slate-900/60 border border-slate-800/80">
                <span className="text-slate-400 capitalize">{key.replace(/_/g, " ")}</span>
                <span className="font-semibold text-slate-200">₹{Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Itemized Transactions */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <h4 className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <CreditCard className="w-3.5 h-3.5 text-amber-400" />
            Itemized Ledger Transactions
          </h4>
          <div className="space-y-2 max-h-[180px] overflow-y-auto">
            {(customer.transactions || []).map((tx, idx) => {
              const isCredit = tx.type === "CREDIT" || tx.transaction_type === "INCOME";
              return (
                <div key={idx} className="flex items-center justify-between text-xs font-mono p-2 rounded-lg bg-slate-900/60 border border-slate-800/80">
                  <div className="flex items-center gap-2">
                    {isCredit ? (
                      <ArrowUpRight className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    ) : (
                      <ArrowDownRight className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                    )}
                    <div>
                      <span className="text-slate-200 font-medium block truncate max-w-[160px]">{tx.merchant || tx.description}</span>
                      <span className="text-[10px] text-slate-500">{tx.date || tx.transaction_date} • {tx.category}</span>
                    </div>
                  </div>
                  <span className={`font-bold ${isCredit ? 'text-emerald-400' : 'text-slate-300'}`}>
                    {isCredit ? '+' : '-'}₹{Number(tx.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
