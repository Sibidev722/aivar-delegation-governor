import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import SecurityMetrics from './components/SecurityMetrics';
import NaturalLanguageInput from './components/NaturalLanguageInput';
import SecurityPanel from './components/SecurityPanel';
import LiveDelegationChain from './components/LiveDelegationChain';
import FinancialResultDashboard from './components/FinancialResultDashboard';
import ScenarioRunner from './components/ScenarioRunner';
import TokenInspector from './components/TokenInspector';
import AuditLedgerView from './components/AuditLedgerView';
import CustomerDataViewer from './components/CustomerDataViewer';
import SystemHealthModal from './components/SystemHealthModal';

import {
  fetchHealth,
  fetchPublicKey,
  fetchPolicies,
  executeAgentA,
  executeGatedTool,
  mintRootToken,
  delegateToken,
  fetchAuditChain,
  verifyAuditChain
} from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState("overview"); // overview | audit | scenarios | customer | tokens
  const [health, setHealth] = useState({ status: "healthy" });
  const [publicKey, setPublicKey] = useState(null);
  const [policies, setPolicies] = useState(null);
  const [activeChainId, setActiveChainId] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [activeScenario, setActiveScenario] = useState(null);
  const [executionResult, setExecutionResult] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);
  const [latestTokenData, setLatestTokenData] = useState(null);
  const [liveCustomerData, setLiveCustomerData] = useState(null);
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(false);

  const [stats, setStats] = useState({
    totalRequests: 0,
    blockedAttacks: 0,
    monotonicityEnforced: 0,
    auditLedgerLinks: 0
  });

  // Initial load
  useEffect(() => {
    loadSystemData();
  }, []);

  const loadSystemData = async () => {
    setIsRefreshing(true);
    try {
      const [h, pk, pol] = await Promise.all([
        fetchHealth(),
        fetchPublicKey(),
        fetchPolicies()
      ]);
      setHealth(h);
      setPublicKey(pk);
      setPolicies(pol);
    } catch (err) {
      console.error("Error loading system data:", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    await loadSystemData();
    if (activeChainId) {
      const auditRes = await fetchAuditChain(activeChainId);
      if (auditRes.ok && Array.isArray(auditRes.data)) {
        setAuditEvents(auditRes.data);
      }
    }
  };

  // Natural Language Prompt Submission (Primary Production Flow)
  const handleNaturalLanguageSubmit = async (userPrompt) => {
    setIsRunning(true);
    setExecutionResult(null);
    setLiveCustomerData(null);

    try {
      const payload = {
        task_type: "financial_analysis_task",
        originating_user: "USER-001",
        customer_id: "CUST-101", // Fallback hint; Agent A Gemini dynamically extracts target from prompt
        operation: "READ_SUMMARY",
        user_prompt: userPrompt,
        use_llm: true
      };

      const result = await executeAgentA(payload);
      setExecutionResult(result);

      if (result.ok && result.data?.chain_id) {
        const chainId = result.data.chain_id;
        setActiveChainId(chainId);

        if (result.data.data) {
          setLiveCustomerData(result.data.data);
        }

        // Fetch cryptographic audit events for this chain
        const auditRes = await fetchAuditChain(chainId);
        if (auditRes.ok && Array.isArray(auditRes.data)) {
          setAuditEvents(auditRes.data);
        }

        // Update safe token inspector data
        setLatestTokenData({
          chain_id: chainId,
          sub: "agent_b",
          aud: "agent_c",
          scopes: ["financials:read:summary"],
          data_scope: { customer_ids: [result.data.customer_id || "CUST-101"] },
          depth: 2,
          max_depth: 4,
          exp: Math.floor(Date.now() / 1000) + 300
        });
      }

      // Update metrics
      setStats((prev) => ({
        totalRequests: prev.totalRequests + 1,
        blockedAttacks: prev.blockedAttacks + (!result.ok ? 1 : 0),
        monotonicityEnforced: prev.monotonicityEnforced + 1,
        auditLedgerLinks: prev.auditLedgerLinks + (result.ok ? 4 : 1)
      }));
    } catch (err) {
      console.error("Execution error:", err);
      setExecutionResult({
        ok: false,
        status: 500,
        data: { message: err.message, error_code: "NETWORK_ERROR" }
      });
    } finally {
      setIsRunning(false);
    }
  };

  // Security Scenario Attack Handler (Secondary Verification Suite)
  const handleRunScenario = async (scenario) => {
    setIsRunning(true);
    setActiveScenario(scenario.id);
    setExecutionResult(null);

    try {
      let result;

      if (scenario.payload.type === "agent_a") {
        result = await executeAgentA(scenario.payload.body);
        if (result.ok && result.data.chain_id) {
          setActiveChainId(result.data.chain_id);
          if (result.data.data) {
            setLiveCustomerData(result.data.data);
          }
          const auditRes = await fetchAuditChain(result.data.chain_id);
          if (auditRes.ok && Array.isArray(auditRes.data)) {
            setAuditEvents(auditRes.data);
          }
        }
      } else if (scenario.payload.type === "agent_c_write_attack") {
        const mintRes = await mintRootToken({
          task_type: "financial_analysis_task",
          target_agent: "agent_a"
        });
        const rootToken = mintRes.data.token;
        const chainId = mintRes.data.chain_id;
        setActiveChainId(chainId);

        const delRes = await delegateToken({
          parent_token: rootToken,
          target_agent: "agent_c",
          requested_scopes: ["financials:read:summary"],
          requested_data_scope: { customer_ids: ["CUST-101"] }
        });
        const tokenC = delRes.data.token;

        result = await executeGatedTool({
          task_id: "scenario_agent_c_write",
          agent_id: "agent_c",
          token: tokenC,
          operation: "WRITE_RECORD",
          resource: "customer_financials",
          customer_id: "CUST-101",
          payload: { summary: "Malicious write attempt" }
        });

        const auditRes = await fetchAuditChain(chainId);
        if (auditRes.ok && Array.isArray(auditRes.data)) {
          setAuditEvents(auditRes.data);
        }
      } else if (scenario.payload.type === "cross_customer_attack") {
        const mintRes = await mintRootToken({
          task_type: "single_customer_audit",
          target_agent: "agent_a"
        });
        const rootToken = mintRes.data.token;
        const chainId = mintRes.data.chain_id;
        setActiveChainId(chainId);

        const delRes = await delegateToken({
          parent_token: rootToken,
          target_agent: "agent_c",
          requested_scopes: ["financials:read:summary"],
          requested_data_scope: { customer_ids: ["CUST-101"] }
        });
        const tokenC = delRes.data.token;

        result = await executeGatedTool({
          task_id: "scenario_cross_cust",
          agent_id: "agent_c",
          token: tokenC,
          operation: "READ_SUMMARY",
          resource: "customer_financials",
          customer_id: "CUST-102"
        });

        const auditRes = await fetchAuditChain(chainId);
        if (auditRes.ok && Array.isArray(auditRes.data)) {
          setAuditEvents(auditRes.data);
        }
      } else if (scenario.payload.type === "tampered_jwt") {
        const mintRes = await mintRootToken({
          task_type: "financial_analysis_task",
          target_agent: "agent_a"
        });
        const parts = mintRes.data.token.split(".");
        const tamperedToken = `${parts[0]}.${parts[1]}.corrupted_signature_payload_xyz`;

        result = await executeGatedTool({
          task_id: "scenario_tamper",
          agent_id: "agent_a",
          token: tamperedToken,
          operation: "READ_SUMMARY",
          resource: "customer_financials",
          customer_id: "CUST-101"
        });
      } else if (scenario.payload.type === "expired_token") {
        const mintRes = await mintRootToken({
          task_type: "financial_analysis_task",
          target_agent: "agent_a",
          ttl_seconds: 1
        });
        const rootToken = mintRes.data.token;
        const chainId = mintRes.data.chain_id;
        setActiveChainId(chainId);

        await new Promise((r) => setTimeout(r, 1100));

        result = await executeGatedTool({
          task_id: "scenario_expired",
          agent_id: "agent_a",
          token: rootToken,
          operation: "READ_SUMMARY",
          resource: "customer_financials",
          customer_id: "CUST-101"
        });

        const auditRes = await fetchAuditChain(chainId);
        if (auditRes.ok && Array.isArray(auditRes.data)) {
          setAuditEvents(auditRes.data);
        }
      } else if (scenario.payload.type === "wrong_audience") {
        const mintRes = await mintRootToken({
          task_type: "financial_analysis_task",
          target_agent: "agent_a"
        });
        const rootToken = mintRes.data.token;
        const chainId = mintRes.data.chain_id;
        setActiveChainId(chainId);

        const delRes = await delegateToken({
          parent_token: rootToken,
          target_agent: "agent_b",
          requested_scopes: ["financials:read:summary"],
          requested_data_scope: { customer_ids: ["CUST-101"] }
        });
        const tokenB = delRes.data.token;

        result = await executeGatedTool({
          task_id: "scenario_wrong_aud",
          agent_id: "agent_c",
          token: tokenB,
          operation: "READ_SUMMARY",
          resource: "customer_financials",
          customer_id: "CUST-101"
        });

        const auditRes = await fetchAuditChain(chainId);
        if (auditRes.ok && Array.isArray(auditRes.data)) {
          setAuditEvents(auditRes.data);
        }
      } else if (scenario.payload.type === "verify_ledger") {
        if (!activeChainId) {
          const mintRes = await mintRootToken({ task_type: "financial_analysis_task" });
          setActiveChainId(mintRes.data.chain_id);
          result = await verifyAuditChain(mintRes.data.chain_id);
        } else {
          result = await verifyAuditChain(activeChainId);
        }
      } else if (scenario.payload.type === "scope_shrinkage") {
        const mintRes = await mintRootToken({ task_type: "financial_analysis_task", target_agent: "agent_a" });
        const tokenA = mintRes.data.token;
        const chainId = mintRes.data.chain_id;
        setActiveChainId(chainId);

        const delB = await delegateToken({
          parent_token: tokenA,
          target_agent: "agent_b",
          requested_scopes: ["financials:read:summary"],
          requested_data_scope: { customer_ids: ["CUST-101"] }
        });

        const delC = await delegateToken({
          parent_token: delB.data.token,
          target_agent: "agent_c",
          requested_scopes: ["financials:read:metrics"],
          requested_data_scope: { customer_ids: ["CUST-101"] }
        });

        result = await executeGatedTool({
          task_id: "scenario_shrink_exec",
          agent_id: "agent_c",
          token: delC.data.token,
          operation: "READ_METRICS",
          resource: "customer_financials",
          customer_id: "CUST-101"
        });

        const auditRes = await fetchAuditChain(chainId);
        if (auditRes.ok && Array.isArray(auditRes.data)) {
          setAuditEvents(auditRes.data);
        }
      }

      setExecutionResult(result);

      setStats((prev) => ({
        totalRequests: prev.totalRequests + 1,
        blockedAttacks: prev.blockedAttacks + (!result.ok ? 1 : 0),
        monotonicityEnforced: prev.monotonicityEnforced + 1,
        auditLedgerLinks: prev.auditLedgerLinks + (result.ok ? 3 : 1)
      }));
    } catch (err) {
      console.error("Scenario error:", err);
      setExecutionResult({
        ok: false,
        status: 500,
        data: { message: err.message, error_code: "CLIENT_EXECUTION_ERROR" }
      });
    } finally {
      setIsRunning(false);
      setActiveScenario(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans">
      <Header
        health={health}
        isRefreshing={isRefreshing}
        onRefresh={handleRefresh}
        onOpenKeyModal={() => setIsKeyModalOpen(true)}
        activeChainId={activeChainId}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        {/* Top Security Metrics Strip */}
        <SecurityMetrics stats={stats} />

        {/* Primary Natural Language Request Interface */}
        <NaturalLanguageInput
          onSubmit={handleNaturalLanguageSubmit}
          isRunning={isRunning}
          defaultPrompt="Read and summarize CUST-101"
        />

        {/* Security & Authorization Status Panel */}
        <SecurityPanel
          executionResult={executionResult}
          isRunning={isRunning}
        />

        {/* Live Multi-Agent Delegation Chain Visualizer */}
        <LiveDelegationChain
          executionResult={executionResult}
          isRunning={isRunning}
          activeChainId={activeChainId}
        />

        {/* Financial Results Display (Populated dynamically from MongoDB) */}
        {liveCustomerData && (
          <FinancialResultDashboard
            financialData={liveCustomerData}
            llmReasoning={executionResult?.data?.llm_reasoning}
            auditEventId={executionResult?.data?.audit_event_id}
          />
        )}

        {/* Navigation Tabs for Deep Governance Inspection */}
        <div className="pt-4 border-t border-slate-800">
          <div className="flex border-b border-slate-800 gap-6 text-sm font-medium">
            <button
              onClick={() => setActiveTab("overview")}
              className={`pb-3 transition-colors border-b-2 font-mono ${
                activeTab === "overview"
                  ? "border-emerald-400 text-white font-bold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              Primary View
            </button>
            <button
              onClick={() => setActiveTab("scenarios")}
              className={`pb-3 transition-colors border-b-2 font-mono ${
                activeTab === "scenarios"
                  ? "border-emerald-400 text-white font-bold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              Security Attack Scenarios
            </button>
            <button
              onClick={() => setActiveTab("audit")}
              className={`pb-3 transition-colors border-b-2 font-mono ${
                activeTab === "audit"
                  ? "border-emerald-400 text-white font-bold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              Audit Ledger ({auditEvents.length} Events)
            </button>
            <button
              onClick={() => setActiveTab("customer")}
              className={`pb-3 transition-colors border-b-2 font-mono ${
                activeTab === "customer"
                  ? "border-emerald-400 text-white font-bold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              All Customer Records (DB)
            </button>
            <button
              onClick={() => setActiveTab("tokens")}
              className={`pb-3 transition-colors border-b-2 font-mono ${
                activeTab === "tokens"
                  ? "border-emerald-400 text-white font-bold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              Token Inspector
            </button>
          </div>
        </div>

        {/* Tab Content Panes */}
        {activeTab === "scenarios" && (
          <ScenarioRunner
            onRunScenario={handleRunScenario}
            isRunning={isRunning}
            activeScenario={activeScenario}
          />
        )}

        {activeTab === "audit" && (
          <AuditLedgerView
            auditEvents={auditEvents}
            activeChainId={activeChainId}
          />
        )}

        {activeTab === "customer" && (
          <CustomerDataViewer
            liveCustomerData={liveCustomerData}
          />
        )}

        {activeTab === "tokens" && (
          <TokenInspector
            tokenData={latestTokenData}
          />
        )}
      </main>

      {/* Cryptographic Key & Policies Modal */}
      <SystemHealthModal
        isOpen={isKeyModalOpen}
        onClose={() => setIsKeyModalOpen(false)}
        publicKey={publicKey}
        policies={policies}
        health={health}
      />
    </div>
  );
}
