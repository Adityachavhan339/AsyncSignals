# AsyncSignals

Multi-chain telemetry and market intelligence for teams, analysts, and ecosystem operators. AsyncSignals turns raw onchain activity into structured signals, live dashboards, and reusable API context.

**Supported chains:** Solana, EVM, Base L2, Polkadot.

## Architecture
<img width="1536" height="1024" alt="1000062461" src="https://github.com/user-attachments/assets/5f882e9a-05e9-47db-8d67-48499e6fb681" />



## Live

- **Dashboard:** [https://asyncsignals.tech](https://asyncsignals.tech)
- **API:** [https://api.asyncsignals.tech](https://api.asyncsignals.tech)
- **API Docs:** [https://api.asyncsignals.tech/docs](https://api.asyncsignals.tech/docs)

## Acknowledgements
Supported by the Alchemy Solana Fund.


## Repository Structure

```text
asyncsignals/
├── backend/                    # Python data pipeline & API
│   ├── api.py                  # FastAPI public API
│   ├── function_app.py         # Core ingestion (prices, whales, news, signals)
│   ├── base.py                 # Base L2 collector
│   ├── polkadot.py             # Polkadot parachain telemetry
│   ├── asyncllm.py             # AI summary generation
│   ├── app.py                  # Streamlit dashboard (legacy)
│   └── requirements.txt
│
├── frontend/                   # Next.js 14 dashboard
│   ├── src/                    # React components & pages
│   ├── package.json
│   ├── next.config.mjs
│   └── tailwind.config.ts
```

## What It Does

- **Live market data** — prices, market cap, and 24h change from CoinGecko and CoinPaprika.
- **Whale flow tracking** — detects large transfers across Solana, EVM, and Base L2, normalizes them to USD, and stores them in Oracle.
- **Signal generation** — execution-oriented alerts such as danger, opportunity, volatility, and SOL flow based on price, whale, and news context.
- **AI summaries** — LLM-generated market context for BTC, SOL, DOT, and Base L2 from stored telemetry.
- **Public API** — FastAPI with JSON and text responses, CORS enabled, and proxy-layer rate limiting.
- **Next.js dashboard** — mission control for whale tracking, signal history, AI context, and chain-specific views.

## Backend Services

| File | Purpose |
|------|---------|----------|
| `function_app.py` | Core ingestion for prices, whales, news, and signals |
| `base.py` | Base L2 collector for blocks, gas, transfers, DEX, and bridge activity |
| `polkadot.py` | Polkadot telemetry for parachains, XCM, governance, and staking |
| `asyncllm.py` | AI summaries for BTC, SOL, DOT, and Base |
| `api.py` | FastAPI public API |

## Frontend Stack

- **Framework:** Next.js 14
- **Styling:** Tailwind CSS
- **Auth:** NextAuth.js with Google OAuth
- **Charts:** Recharts / Plotly
- **Deployment:** PM2 cluster with Nginx load balancing

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Data Sources | CoinGecko, CoinPaprika, Alchemy, Helius, Dotlake, NewsData | Market and onchain data |
| Workers | Python 3.12, httpx, asyncio, oracledb | Data ingestion |
| Database | Oracle 26ai Autonomous | Persistent storage |
| API | FastAPI, uvicorn, pydantic | Public REST API |
| Frontend | Next.js 14, React, Tailwind, NextAuth | Dashboard |
| Reverse Proxy | Nginx, Let's Encrypt | SSL and load balancing |
| Process Management | systemd, PM2 | Auto-restart and clustering |
| Infrastructure | Oracle Cloud Ampere A1 | 2 OCPU, 12 GB RAM, 2 Gbps |

## Performance

| Metric | Value |
|--------|-------|
| API sustained RPS | 300 req/s |
| API burst RPS | 800 req/s |
| Concurrent users | 150 |

## Security

- TLS via Let's Encrypt
- Oracle Wallet for DB authentication
- NextAuth.js with Google OAuth
- Rate limiting via Nginx
- CORS enabled for API

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Adityachavhan339/AsyncSignals.git
cd AsyncSignals
```

### 2. Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your credentials.

### 3. Frontend setup

```bash
cd ../frontend
npm install
cp .env.local.example .env.local
```

Edit `.env.local` with your API URLs.

## Environment Variables

Required variables include:

- **Oracle DB:** `DB_USER`, `DB_PASSWORD`, `DB_DSN`, `WALLET_DIR`
- **Market data:** `COINGECKO_KEY`, `NEWSDATA_KEY`
- **Onchain:** `ALCHEMY_KEY`, `SOLANA_DRPC_URL`, `HELIUS_API_KEY`
- **Polkadot:** `DOTLAKE_API_PARITY_KEY`, `PUBLICNODE_POLKADOT_URL`
- **AI:** `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`
- **Alerts:** `TELEGRAM_BOT_TOKEN`

See `backend/.env.example` for the full list.

## Run

### Backend API

```bash
cd backend
source .venv/bin/activate
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend

```bash
cd frontend
npm run dev
npm run build
npm start
```

### Workers

```bash
cd backend
python function_app.py
python base.py
python polkadot.py
python asyncllm.py
```

## Architecture

```text
External sources -> Workers -> Oracle DB -> Nginx -> Next.js / FastAPI
```


- **Database:** Oracle Cloud 26ai Always Free
- **API:** FastAPI with RAM cache, auto-refresh, and proxy-layer controls
- **Dashboard:** Next.js 14 with SSR, PM2 cluster, and Nginx load balancing
- **Infra:** Oracle VM, Nginx reverse proxy, Let's Encrypt SSL, and service auto-restart


## Product Direction

AsyncSignals is built as developer-facing telemetry infrastructure, not a retail trading tool. It is designed for research teams, ecosystem operators, analysts, and builders who need clean, reusable onchain signal data.

## License

Apache 2.0
