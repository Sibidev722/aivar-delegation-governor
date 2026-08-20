# Production Deployment & Architecture Guide
## Delegation Chain Enforcement Layer (Multi-Agent Cryptographic Scope Bounding)

This system provides a production-grade, enterprise-ready **Delegation Chain Enforcement Layer** that propagates signed, scope-bounded permission tokens across multi-agent calls (Agent A → Agent B → Agent C → Delegation Governor → Tool Gateway) to mathematically eliminate silent scope expansion.

---

## 1. Problem Statement Requirements Mapping

| Evaluation Requirement | Technical Architecture & Implementation | Source File Link |
| :--- | :--- | :--- |
| **Delegation Token Format** | Cryptographically signed Ed25519 tokens containing `originating_user`, `task_id`, `max_allowed_scope`, `current_delegation_depth`, `exp`, `jti`, `chain_id`, `data_scope`, `resource`. | [`security.py`](file:///c:/Users/Sibi/Governance-AI/backend/app/core/security.py#L30-L156)<br>[`token.py`](file:///c:/Users/Sibi/Governance-AI/backend/app/models/token.py#L1-L60) |
| **Token Propagation Mechanism** | When Agent A delegates to Agent B, `derive_child_token` validates strict monotonic scope shrinkage (`is_scope_subset` & `is_data_scope_subset`). A child token **cannot** possess broader authority than its parent. | [`governor_service.py`](file:///c:/Users/Sibi/Governance-AI/backend/app/services/governor_service.py#L168-L260)<br>[`scope_engine.py`](file:///c:/Users/Sibi/Governance-AI/backend/app/services/scope_engine.py#L35-L190) |
| **Enforcement Interceptor (Governor PEP)** | Sole authorized gateway (`POST /api/v1/governor/tools/execute`) validates Ed25519 signature, audience, scopes, customer boundary, and depth prior to invoking protected tools. | [`tools.py`](file:///c:/Users/Sibi/Governance-AI/backend/app/api/v1/endpoints/tools.py#L35-L199)<br>[`financial_tool.py`](file:///c:/Users/Sibi/Governance-AI/backend/app/services/financial_tool.py#L22-L50) |
| **Delegation Audit Log** | Tamper-evident MongoDB audit ledger with cryptographic SHA-256 event hash linking (`prev_event_hash`), reconstructing the complete call chain (`GET /api/v1/audit/chain/{chain_id}`). | [`audit_service.py`](file:///c:/Users/Sibi/Governance-AI/backend/app/services/audit_service.py#L1-L200)<br>[`audit.py`](file:///c:/Users/Sibi/Governance-AI/backend/app/api/v1/endpoints/audit.py#L1-L70) |
| **Success Criterion 1**: 3-Agent Read Chain & Reject Agent C Write | Read-only tokens (`financials:read:summary`) flow through A → B → C. If Agent C attempts `WRITE_RECORD`, Governor PEP blocks execution with `403 INSUFFICIENT_OPERATION_SCOPE`. | [`ScenarioRunner.jsx`](file:///c:/Users/Sibi/Governance-AI/frontend/src/components/ScenarioRunner.jsx#L34-L44) |
| **Success Criterion 2**: Reject Scope Expansion Attempt | An attempt by Agent A or B to derive a token with broader scope (`financials:write:record`) than its parent is rejected with `403 SCOPE_EXPANSION_FORBIDDEN`. | [`ScenarioRunner.jsx`](file:///c:/Users/Sibi/Governance-AI/frontend/src/components/ScenarioRunner.jsx#L47-L63) |
| **Success Criterion 3**: Audit Chain Reconstruction | Reconstruction of full delegation chain (`USER-001 → agent_a → agent_b → agent_c → financial_tool`) with 100% cryptographic SHA-256 ledger integrity verification. | [`AuditLedgerView.jsx`](file:///c:/Users/Sibi/Governance-AI/frontend/src/components/AuditLedgerView.jsx#L1-L150) |
| **Success Criterion 4**: Token Expiry Enforcement | Expired tokens (`now > exp`) presented mid-chain are immediately rejected with `401 TOKEN_EXPIRED`. | [`ScenarioRunner.jsx`](file:///c:/Users/Sibi/Governance-AI/frontend/src/components/ScenarioRunner.jsx#L89-L97) |
| **Bonus**: Scope Shrinkage | Monotonic authority reduction: Root `financials:read:all` → Agent B `financials:read:summary` → Agent C `financials:read:summary`. Data scope bounded per customer (`CUST-0101` to `CUST-0500`). | [`agents.py`](file:///c:/Users/Sibi/Governance-AI/backend/app/api/v1/endpoints/agents.py#L78-L110) |

---

## 2. Quickstart Deployment (Local Docker Compose)

To launch the complete production system locally in Docker containers:

```bash
# 1. Clone repository & enter workspace
cd Governance-AI

# 2. Build and launch backend & frontend containers
docker compose up --build -d

# 3. Verify health status
curl http://localhost:8000/api/v1/health
```

- **Frontend Dashboard**: `http://localhost:5173/` or `http://localhost/`
- **Backend Swagger API Specs**: `http://localhost:8000/docs`

---

## 3. Production Deployment Guide (AWS Infrastructure)

### Option A: AWS App Runner / ECS Fargate (Recommended)

1. **Build and push images to AWS ECR**:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

   docker build -t governance-ai-backend ./backend
   docker tag governance-ai-backend:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/governance-ai-backend:latest
   docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/governance-ai-backend:latest

   docker build -t governance-ai-frontend ./frontend
   docker tag governance-ai-frontend:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/governance-ai-frontend:latest
   docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/governance-ai-frontend:latest
   ```

2. **Deploy Backend Service on AWS App Runner / ECS**:
   - Environment Variables:
     - `MONGODB_URI`: `mongodb+srv://...`
     - `GEMINI_API_KEY`: `<YOUR_GEMINI_API_KEY>`
     - `ED25519_PRIVATE_KEY_HEX`: `1337133713371337133713371337133713371337133713371337133713371337`
   - Port: `8000`
   - Health Check Path: `/api/v1/health`

---

## 4. Live Verification API Endpoints

- **Execute Natural Language Prompt (Gemini Powered)**:
  `POST /api/v1/agents/agent-a/execute`
- **Derive Child Token (Monotonicity Enforced)**:
  `POST /api/v1/governor/tokens/delegate`
- **Execute Protected Financial Tool**:
  `POST /api/v1/governor/tools/execute`
- **Fetch Audit Chain**:
  `GET /api/v1/audit/chain/{chain_id}`
- **Verify Cryptographic Audit Hash Chain**:
  `GET /api/v1/audit/verify/{chain_id}`
