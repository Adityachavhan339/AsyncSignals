# AsyncSignals
AsyncSignals is a Solana-first telemetry and market intelligence product that turns raw onchain and market activity into structured signals, operator dashboards, and reusable AI context. The project combines a live dashboard, background ingestion jobs, signal generation, whale flow tracking, and model-generated summaries into one research surface.

#Acknowledgements

AsyncSignals is grateful for support from the Alchemy Solana Fund.

## What it does

- Tracks live market context from external crypto market and news sources.
- Detects whale activity across Solana and EVM flows, then stores normalized rows in Oracle-backed tables.
- Generates execution-oriented signals such as danger, opportunity, volatility, and SOL flow alerts.
- Produces concise AI summaries for assets like BTC and SOL using stored market context.
- Exposes everything through a Streamlit dashboard designed for teams, analysts, and ecosystem operators.

## Repository structure

```text
asyncsignals/
├── app.py
├── function_app.py
├── asyncllm.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

### Main files

- `app.py` — Streamlit dashboard and access surface for market, whale, signal, alert, and AI summary views.
- `function_app.py` — background ingestion, Solana and EVM whale parsing, news and price collection, signal generation, database writes, and Telegram alert broadcasting. 
- `asyncllm.py` — AI summary generation layer for turning stored market context into readable BTC and SOL summaries.

## Core features

| Feature | Description |
|---|---|
| Dashboard UI | Multi-tab Streamlit interface for mission control, whales, signals, AI context, news, market surface, and alerts. |
| Solana telemetry | Parses SOL-linked transaction activity and extracts whale-style transfer rows from Solana RPC responses. |
| Cross-chain whale flow | Pulls EVM asset transfer activity and ranks large transfers using token price lookups. |
| Signal engine | Builds operator-facing signal rows based on price movement, whale activity, and news context. |
| AI summaries | Uses LLM providers to generate short market summaries from database context. |
| Alert routing | Stores subscribers and sends selected alerts through Telegram. |

## Setup

1. Clone the repository.
2. Create a virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and fill in the required credentials.
5. Rename the files to `app.py`, `function_app.py`, and `asyncllm.py` if they are still using older names.

## Environment variables

This project expects secrets for database access and third-party APIs. The code references variables for Oracle credentials, wallet configuration, crypto data sources, Solana RPC access, Telegram alerts, and LLM providers, so public repositories should only include placeholders in `.env.example`, not live credentials.

Typical variables include:

- `DBUSER`
- `DBPASSWORD`
- `DBDSN`
- `WALLETDIR`
- `COINGECKOKEY`
- `NEWSDATAKEY`
- `ALCHEMYKEY`
- `SOLANADRPCURL`
- `TELEGRAMBOTTOKEN`
- `CEREBRASAPIKEY`
- `GROQAPIKEY`
- `GEMINIAPIKEY` 

## Running the project

### Dashboard

```bash
streamlit run app.py
```

### Backend ingestion worker

```bash
python function_app.py
```

### AI summary worker

```bash
python asyncllm.py
```


## Product direction

AsyncSignals is built as a Solana-first observability and intelligence layer rather than a simple retail dashboard. The dashboard copy and backend logic both position it for research teams, analysts, ecosystem operators, and signal-driven workflows.
