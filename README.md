# AsyncSignals

Multi-chain telemetry and market intelligence for teams, analysts, and ecosystem operators. Turns raw onchain activity into structured signals, live dashboards, and reusable API context.

Supported chains: Solana, EVM, Base L2, Polkadot.

---
##Technical Flowchart##
<img width="1536" height="1024" alt="1000062409" src="https://github.com/user-attachments/assets/e53d4600-fa1b-456e-ad35-a0d0707bc4e4" />



## What it does

- **Live market data** — prices, market cap, 24h change from CoinGecko and CoinPaprika.
- **Whale flow tracking** — detects large transfers across Solana, EVM, and Base L2, normalizes to USD, stores in Oracle.
- **Signal generation** — execution-oriented alerts: danger, opportunity, volatility, SOL flow, based on price + whale + news context.
- **AI summaries** — LLM-generated market context for BTC, SOL, DOT, and Base L2 from stored telemetry.
- **Public API** — FastAPI with 17 endpoints, JSON + text formats, CORS-enabled, rate-limited via Nginx.
- **Streamlit dashboard** — mission control, whale tracker, signal ledger, AI context, chain-specific tabs.

---

## Live

- Dashboard: [https://asyncsignals.tech]
- API: [https://api.asyncsignals.tech/docs]
- API root: `curl https://api.asyncsignals.tech/`

---

## Acknowledgements

Supported by the [Alchemy Solana Fund](https://www.alchemy.com/solana-20m-fund).

---

## Repository

```text
asyncsignals/
├── app.py              # Streamlit dashboard
├── api.py              # FastAPI public API
├── function_app.py     # Core ingestion worker (prices, whales, news, signals)
├── base.py             # Base L2 collector (blocks, gas, transfers, DEX, bridge)
├── polkadot.py         # Polkadot collector (parachains, XCM, gov, staking)
├── asyncllm.py         # AI summary worker (BTC, SOL, DOT, Base)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Core features

| Feature | Description |
|---|---|
| Dashboard | Multi-tab Streamlit: market, whales, signals, AI summaries, Polkadot, Base L2, alerts. |
| Public API | 17 endpoints: `/market`, `/whales`, `/signals`, `/polkadot`, `/base`, `/bundle`, etc. |
| Whale flow | Solana (RPC), EVM (Alchemy), Base L2 (5 RPC providers). Normalized to USD. |
| Signal engine | Danger / opportunity / volatility alerts based on price + whale + news. |
| AI summaries | Multi-provider LLM fallback (Groq, Cerebras, OpenRouter, Gemini). |
| Chain telemetry | Polkadot: parachain activity, XCM, governance, staking. Base L2: sequencer, gas, DEX, bridge. |
| Alert routing | Telegram bot for subscriber notifications. |

---

## Setup

```bash
git clone https://github.com/Adityachavhan339/asyncsignals.git
cd asyncsignals
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
```

---

## Environment

Required variables (see `.env.example` for full list):

- Oracle DB: `DB_USER`, `DB_PASSWORD`, `DB_DSN`, `WALLET_DIR`
- Market data: `COINGECKO_KEY`, `NEWSDATA_KEY`
- Onchain: `ALCHEMY_KEY`, `SOLANA_DRPC_URL`, `HELIUS_API_KEY`
- Polkadot: `DOTLAKE_API_PARITY_KEY`, `PUBLICNODE_POLKADOT_URL`
- AI: `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`
- Alerts: `TELEGRAM_BOT_TOKEN`

---

## Run

### Dashboard
```bash
streamlit run app.py
```

### API
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 2
```

### Workers (cron)
```bash
# Core ingestion — every 5 minutes
python function_app.py

# Base L2 — every 5 minutes (offset +1)
python base.py

# Polkadot — every 5 minutes (offset +2)
python polkadot.py

# AI summaries — every 2 hours
python asyncllm.py
```

---

## Architecture

```
External sources → Workers → Oracle DB → Nginx → Streamlit / FastAPI
```

- **Workers**: 4 cron-scheduled Python processes (function_app, base, polkadot, asyncllm).
- **Database**: Oracle Cloud 26ai Always Free (14+ tables).
- **API**: FastAPI with RAM cache, auto-refresh, 500+ RPS cached.
- **Dashboard**: Streamlit with hosted auth, multi-tab, exportable tables.
- **Infra**: Oracle VM, Nginx reverse proxy, Let's Encrypt SSL, systemd auto-restart.

---

## Product direction

Built as developer-facing telemetry infrastructure, not a retail trading tool. Target: research teams, ecosystem operators, analysts, and builders who need clean onchain signal data.

Open source under Apache 2.0.
