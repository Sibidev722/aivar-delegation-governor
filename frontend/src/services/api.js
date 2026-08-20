const BASE_URL = import.meta.env.VITE_API_URL || "";
const API_BASE = `${BASE_URL}/api/v1`;

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    return await res.json();
  } catch (err) {
    return { status: "offline", error: err.message };
  }
}

export async function fetchReadiness() {
  try {
    const res = await fetch(`${API_BASE}/health/ready`);
    return await res.json();
  } catch (err) {
    return { status: "offline", error: err.message };
  }
}

export async function fetchPublicKey() {
  try {
    const res = await fetch(`${API_BASE}/governor/public-key`);
    return await res.json();
  } catch (err) {
    return { error: err.message };
  }
}

export async function fetchPolicies() {
  try {
    const res = await fetch(`${API_BASE}/governor/policies`);
    return await res.json();
  } catch (err) {
    return { policies: {} };
  }
}

export async function executeAgentA(payload) {
  const res = await fetch(`${API_BASE}/agents/agent-a/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}

export async function executeGatedTool(payload) {
  const res = await fetch(`${API_BASE}/governor/tools/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}

export async function mintRootToken(payload) {
  const res = await fetch(`${API_BASE}/governor/tokens/mint-root`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}

export async function delegateToken(payload) {
  const res = await fetch(`${API_BASE}/governor/tokens/delegate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}

export async function validateToken(payload) {
  const res = await fetch(`${API_BASE}/governor/tokens/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}

export async function fetchAuditChain(chainId) {
  try {
    const res = await fetch(`${API_BASE}/audit/chain/${chainId}`);
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

export async function verifyAuditChain(chainId) {
  try {
    const res = await fetch(`${API_BASE}/audit/verify/${chainId}`);
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}
