# AsyncSignals

Multi-chain telemetry and market intelligence for teams, analysts, and ecosystem operators. AsyncSignals turns raw onchain activity into structured signals, live dashboards, and reusable API context.

**Supported chains:** Solana, EVM, Base L2, Polkadot, Sui.

---

## Architecture

<img width="1402" height="1122" alt="1000062575" src="https://github.com/user-attachments/assets/bd622607-b166-4441-ac76-a554aa282575" />


External Sources → Python Workers → Oracle DB → FastAPI → Next.js Dashboard

---

## Live

- **Dashboard:** https://asyncsignals.tech  
- **API:** https://api.asyncsignals.tech  
- **API Docs:** https://api.asyncsignals.tech/docs  

---

## Acknowledgements

Supported by the Alchemy Solana Fund.

---

## What It Does

- Multi-chain real-time market + onchain data aggregation  
- Whale tracking across Solana, EVM, Base L2, Sui  
- Execution-level signal generation (DANGER / OPPORTUNITY / VOLATILITY)  
- AI-powered cross-chain intelligence summaries  
- NodeOps infrastructure monitoring + diagnostics  
- Unified REST API for builders, researchers, and bots  
- Full mission-control dashboard for ecosystem analytics  

---

## Backend Services

| File | Purpose |
|------|---------|
| `function_app.py` | Core ingestion pipeline (prices, whales, news, signals) |
| `base.py` | Base L2 telemetry (gas, DEX, bridges, whale flows) |
| `polkadot.py` | Polkadot governance, staking, XCM, validator analytics |
| `sui.py` | Sui Move ecosystem telemetry (protocols, whales, objects, exposure) |
| `nodeops_telemetry.py` | Node health monitoring, runbooks, error classification, metrics |
| `asyncllm.py` | Multi-provider AI summaries + cross-chain intelligence fusion |
| `api.py` | FastAPI layer (cached endpoints + aggregation + public API) |

---

## Key Modules

### Base L2 (base.py)
- Multi-provider RPC redundancy (Alchemy, ChainStack, BlockPI, NodeReal)
- Gas fee tracking + sequencer health monitoring
- Whale detection + bridge flow analysis
- DEX activity tracking (Aerodrome)
- **Purpose:** Detect liquidity shifts, congestion spikes, and whale-driven volatility

---

### Polkadot (polkadot.py)
- PublicNode + DotLake integration
- Staking, governance, treasury tracking
- XCM message + transfer monitoring
- Validator performance + health scoring
- **Purpose:** Monitor ecosystem governance, staking security, and cross-chain messaging activity

---

### Sui (sui.py)
- Ankr GraphQL Move ecosystem ingestion
- Object + transaction decoding
- Protocol detection (Cetus, DeepBook, Scallop, Navi, Suilend, Turbos, FlowX, Kriya, Aftermath, Bucket)
- Whale tracking (≥500 SUI or ≥$100)
- Protocol exposure analytics
- **Purpose:** Track Move ecosystem liquidity, whale accumulation, and protocol dominance shifts

---

### NodeOps Telemetry (nodeops_telemetry.py)
- Node runtime health monitoring system
- Error classification + runbook mapping
- Severity scoring (critical / warning / healthy)
- CSV export for ops + finance teams
- Demo data generator for testing
- **Purpose:** Provide production-grade infrastructure observability and failure diagnostics

---

### AI Layer (asyncllm.py)
- Multi-provider fallback LLM system (Groq, Cerebras, OpenRouter, Gemini, Cloudflare)
- Cross-chain context fusion (prices + whales + news + telemetry)
- Asset intelligence summaries (BTC, SOL, DOT, BASE, SUI, NODEOPS)
- Oracle-persisted AI outputs
- **Purpose:** Convert raw telemetry into structured market intelligence

---

### API Layer (api.py)
- FastAPI REST + text API layer
- 120s RAM cache system for performance
- CORS enabled for dashboard + external integrations
- AI-assisted Solana error decoder
- **Purpose:** Unified high-performance data + intelligence serving layer

---

## Frontend Stack

- **Framework:** Next.js 14 (App Router)
- **Styling:** Tailwind CSS
- **Auth:** NextAuth.js (Google OAuth + wallet authentication)
- **Charts:** Recharts + Plotly
- **Rendering:** SSR + client hydration hybrid model
- **Deployment:** PM2 cluster mode
- **Reverse Proxy:** Nginx + SSL (Let’s Encrypt)

---

## Technology Stack

| Layer | Technology | Purpose |
|------|------------|----------|
| Data Sources | CoinGecko, CoinPaprika, Alchemy, Helius, Ankr, DotLake, NewsData | Market + onchain + news ingestion |
| Workers | Python 3.12, asyncio, httpx | High-frequency async data ingestion |
| Database | Oracle Autonomous DB 26ai | Persistent telemetry + signals storage |
| API Layer | FastAPI, uvicorn, pydantic | High-performance REST + cached APIs |
| Frontend | Next.js 14, React, Tailwind CSS | Real-time analytics dashboard |
| Infrastructure | Oracle Cloud Ampere A1 VM | Scalable compute for workers + API |
| Process Management | systemd + PM2 | Auto-restart + production reliability |
| Reverse Proxy | Nginx + Let’s Encrypt | SSL termination + rate limiting + routing |

---

## Performance

| Metric | Value |
|------|----------|
| Sustained API Load | 300 req/s |
| Burst Capacity | 800 req/s |
| Concurrent Users | ~150 |
| Data Refresh Cycle | 5 minutes |
| AI Summary Cycle | 2 hours |

---

## Architecture Flow (Production)

```text
External Data Sources
        ↓
Python Async Workers
        ↓
Oracle Autonomous Database
        ↓
FastAPI Cache + Aggregation Layer
        ↓
Next.js Dashboard (Mission Control UI)
        ↓
External Consumers (APIs / Bots / Researchers / Partners)
