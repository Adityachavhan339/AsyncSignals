import asyncio
import os
from datetime import datetime, UTC
from typing import Callable, Awaitable

import httpx
import oracledb
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

WALLET_DIR = os.getenv("WALLET_DIR", "/home/ubuntu/wallet")
DB_DSN = os.getenv("DB_DSN", "asyncsignalsdatabase_high")


def get_connection():
    return oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        config_dir=WALLET_DIR,
        wallet_location=WALLET_DIR,
        wallet_password=DB_PASSWORD,
    )


def utc_now_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def fetch_context_from_db() -> str:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        prices_text = ""
        whales_text = ""
        news_text = ""
        polkadot_text = ""
        base_text = ""
        bnb_text = ""

        cursor.execute("""
            SELECT symbol, current_price, market_cap, price_change_percentage_24h
            FROM prices
            FETCH FIRST 25 ROWS ONLY
        """)
        prices_rows = cursor.fetchall()
        prices_text = "\n".join(
            f"{r[0]} price={r[1]} market_cap={r[2]} change_24h={r[3]}"
            for r in prices_rows
        )

        cursor.execute("""
            SELECT time, asset, amount, raw_qty, from_address, to_address
            FROM whales
            ORDER BY time DESC
            FETCH FIRST 25 ROWS ONLY
        """)
        whales_rows = cursor.fetchall()
        whales_text = "\n".join(
            f"{r[0]} asset={r[1]} amount={r[2]} raw_qty={r[3]} from={r[4]} to={r[5]}"
            for r in whales_rows
        )

        cursor.execute("""
            SELECT title, source_id, pubdate, description
            FROM news
            ORDER BY pubdate DESC
            FETCH FIRST 15 ROWS ONLY
        """)
        news_rows = cursor.fetchall()
        news_text = "\n".join(
            f"{r[2]} | {r[1]} | {r[0]} | {str(r[3])[:300]}"
            for r in news_rows
        )

        cursor.execute("""
            SELECT relay_chain, chain_name, tx_count, tps, total_fees_usd, activity_score, alert_level
            FROM POLKADOT_CHAIN_ACTIVITY_DAILY
            WHERE activity_date = (SELECT MAX(activity_date) FROM POLKADOT_CHAIN_ACTIVITY_DAILY)
            ORDER BY activity_score DESC
            FETCH FIRST 10 ROWS ONLY
        """)
        polkadot_rows = cursor.fetchall()
        polkadot_text = "\n".join(
            f"{r[0]} | {r[1]} | tx={r[2]} tps={r[3]:.3f} fees_usd={r[4]} score={r[5]} alert={r[6]}"
            for r in polkadot_rows
        )

        cursor.execute("""
            SELECT signal_date, signal_family, chain_name, severity, score, title, description
            FROM POLKADOT_DERIVED_SIGNALS
            ORDER BY signal_date DESC, score DESC
            FETCH FIRST 10 ROWS ONLY
        """)
        polkadot_signals = cursor.fetchall()
        if polkadot_signals:
            polkadot_text += "\n\nPolkadot Signals:\n"
            polkadot_text += "\n".join(
                f"[{r[3]}] {r[4]} | {r[1]} | {r[2]} | {r[5]}"
                for r in polkadot_signals
            )

        cursor.execute("""
            SELECT activity_date, chain_name, tx_count, tps, total_fees_usd, activity_score, alert_level
            FROM BASE_CHAIN_ACTIVITY_DAILY
            ORDER BY activity_date DESC
            FETCH FIRST 1 ROWS ONLY
        """)
        base_rows = cursor.fetchall()
        base_text = "\n".join(
            f"{r[0]} | {r[1]} | tx={r[2]} tps={r[3]:.3f} fees_usd={r[4]} score={r[5]} alert={r[6]}"
            for r in base_rows
        )

        cursor.execute("""
            SELECT signal_date, signal_family, severity, score, title, description
            FROM BASE_DERIVED_SIGNALS
            ORDER BY signal_date DESC, score DESC
            FETCH FIRST 10 ROWS ONLY
        """)
        base_signals = cursor.fetchall()
        if base_signals:
            base_text += "\n\nBase Signals:\n"
            base_text += "\n".join(
                f"[{r[2]}] {r[3]} | {r[1]} | {r[4]}"
                for r in base_signals
            )

        cursor.execute("""
            SELECT captured_at, latest_block_number, tps_1min, gas_price_gwei, tx_count
            FROM BNB_RPC_SNAPSHOT
            ORDER BY captured_at DESC
            FETCH FIRST 1 ROWS ONLY
        """)
        bnb_rpc_rows = cursor.fetchall()
        if bnb_rpc_rows:
            r = bnb_rpc_rows[0]
            bnb_text = f"BNB RPC: block={r[1]} tps={r[2]} gas={r[3]} tx_count={r[4]}"

        cursor.execute("""
            SELECT timestamp, asset_symbol, value_usd, from_address, to_address, transfer_type
            FROM BNB_WHALE_EVENTS
            ORDER BY timestamp DESC
            FETCH FIRST 15 ROWS ONLY
        """)
        bnb_whale_rows = cursor.fetchall()
        if bnb_whale_rows:
            bnb_text += "\nBNB Whales:\n"
            bnb_text += "\n".join(
                f"{r[0]} | {r[1]} | usd={r[2]} | {r[3]} -> {r[4]} | type={r[5]}"
                for r in bnb_whale_rows
            )

        cursor.execute("""
            SELECT signal_date, signal_family, severity, score, title, description
            FROM BNB_DERIVED_SIGNALS
            ORDER BY signal_date DESC, score DESC
            FETCH FIRST 10 ROWS ONLY
        """)
        bnb_signals = cursor.fetchall()
        if bnb_signals:
            bnb_text += "\n\nBNB Signals:\n"
            bnb_text += "\n".join(
                f"[{r[2]}] {r[3]} | {r[1]} | {r[4]}"
                for r in bnb_signals
            )

        cursor.execute("""
            SELECT tx_hash, event_timestamp, token, amount, usd_value, protocol_tag, direction
            FROM SUI_WHALE_EVENTS
            ORDER BY event_timestamp DESC
            FETCH FIRST 15 ROWS ONLY
        """)
        sui_rows = cursor.fetchall()
        sui_text = "\n".join(
            f"{r[1]} | {r[2]} | amount={r[3]} | usd={r[4]} | proto={r[5]} | dir={r[6]}"
            for r in sui_rows
        )

        cursor.execute("""
            SELECT protocol, volume_usd, tx_count
            FROM SUI_PROTOCOL_EXPOSURE
            ORDER BY volume_usd DESC
            FETCH FIRST 8 ROWS ONLY
        """)
        sui_proto_rows = cursor.fetchall()
        if sui_proto_rows:
            sui_text += "\n\nSui Protocol Exposure:\n"
            sui_text += "\n".join(
                f"{r[0]} | vol=${r[1]} | txs={r[2]}"
                for r in sui_proto_rows
            )

        cursor.execute("""
            SELECT node_id, chain, ts, success_rate, avg_latency_ms, error_code, runbook_advice
            FROM NODEOPS_METRICS
            WHERE ts >= SYSTIMESTAMP - INTERVAL '24' HOUR
            ORDER BY ts DESC
            FETCH FIRST 10 ROWS ONLY
        """)
        nodeops_rows = cursor.fetchall()
        nodeops_text = "\n".join(
            f"{r[0]} | {r[1]} | success={r[3]}% | latency={r[4]}ms | err={r[5] or 'none'}"
            for r in nodeops_rows
        )

        return (
            "=== PRICES ===\n"
            f"{prices_text}\n\n"
            "=== WHALES ===\n"
            f"{whales_text}\n\n"
            "=== NEWS ===\n"
            f"{news_text}\n\n"
            "=== POLKADOT ===\n"
            f"{polkadot_text}\n\n"
            "=== BASE ===\n"
            f"{base_text}\n\n"
            "=== BNB ===\n"
            f"{bnb_text}\n\n"
            "=== SUI ===\n"
            f"{sui_text}\n\n"
            "=== NODEOPS ===\n"
            f"{nodeops_text}"

        )
    
    finally:
        cursor.close()
        conn.close()

def sanitize_error_message(err: Exception) -> str:
    msg = str(err)
    secrets = [
        GEMINI_API_KEY,
        GROQ_API_KEY,
        CEREBRAS_API_KEY,
        OPENROUTER_API_KEY,
        CLOUDFLARE_API_TOKEN,
        CLOUDFLARE_ACCOUNT_ID,
    ]
    for secret in secrets:
        if secret:
            msg = msg.replace(secret, "[REDACTED]")
    return msg


async def call_cerebras(client: httpx.AsyncClient, prompt: str, system_instruction: str) -> str:
    if not CEREBRAS_API_KEY:
        raise ValueError("Missing CEREBRAS_API_KEY")

    resp = await client.post(
        "https://api.cerebras.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {CEREBRAS_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-oss-120b",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        },
        timeout=25.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


async def call_groq(client: httpx.AsyncClient, prompt: str, system_instruction: str) -> str:
    if not GROQ_API_KEY:
        raise ValueError("Missing GROQ_API_KEY")

    resp = await client.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        },
        timeout=25.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


async def call_gemini(client: httpx.AsyncClient, prompt: str, system_instruction: str) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("Missing GEMINI_API_KEY")

    model = "gemini-2.5-flash"
    resp = await client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_instruction}\n\nContext:\n{prompt}"}
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.2},
        },
        timeout=25.0,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

async def call_openrouter(client: httpx.AsyncClient, prompt: str, system_instruction: str) -> str:
    if not OPENROUTER_API_KEY:
        raise ValueError("Missing OPENROUTER_API_KEY")

    resp = await client.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://asyncsignals.tech",
            "X-OpenRouter-Title": "AsyncSignals",
        },
        json={
            "model": "google/gemma-4-31b-it:free",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


async def call_cloudflare(client: httpx.AsyncClient, prompt: str, system_instruction: str) -> str:
    if not CLOUDFLARE_API_TOKEN:
        raise ValueError("Missing CLOUDFLARE_API_TOKEN")
    if not CLOUDFLARE_ACCOUNT_ID:
        raise ValueError("Missing CLOUDFLARE_ACCOUNT_ID")

    resp = await client.post(
        f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "model": "@cf/meta/llama-3.1-8b-instruct",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()

def build_rule_based_summary(context: str, asset: str) -> str:
    asset = asset.upper()
    if asset == "BTC":
        return (
            "BTC summary is running on fallback mode. Price, whale flow, and news ingestion remain active, "
            "but upstream language models are temporarily unavailable. Review the live dashboard for current "
            "price behavior, recent whale transfers, and the latest market headlines."
        )
    if asset == "SOL":
        return (
            "SOL summary is running on fallback mode. Solana price data, whale flow monitoring, and news ingestion "
            "remain active while language-model providers recover. Review live wallet flow, token activity, and "
            "headline context directly in the dashboard."
        )
    if asset == "DOT":
        return (
            "DOT summary is running on fallback mode. Polkadot parachain telemetry, staking data, treasury flows, "
            "and XCM cross-chain activity remain active. Review the Polkadot tab for live chain activity, "
            "governance signals, and validator economics."
        )
    if asset == "BASE":
        return (
            "Base summary is running on fallback mode. Base L2 chain activity, whale transfers, gas metrics, "
            "and DEX/bridge signals remain active. Review the Base L2 tab for live sequencer throughput, "
            "builder velocity, and fee pressure indicators."
        )
    if asset == "BNB":
        return (
            "BNB summary is running on fallback mode. BNB Chain telemetry, whale transfers, "
            "DEX pool risk scores, validator health, and gas forecasts remain active. "
            "Review the BNB tab for live throughput, builder velocity, and fee pressure indicators."
        )
    return (
        f"{asset} summary is temporarily running on fallback mode. Core telemetry remains active even though "
        f"language-model providers are currently unavailable."
    )

def generate_nodeops_runbook(error_code: str, node_context: str) -> str:
    runbooks = {
        "NODE_OVERLOADED": (
            "Node is processing more jobs than its resource allocation allows. "
            "CPU or memory saturation is causing degraded performance."
        ),
        "RPC_UNAVAILABLE": (
            "Primary RPC endpoint is unreachable. This may be a network partition, "
            "provider outage, or firewall/DNS issue."
        ),
        "NONCE_TOO_LOW": (
            "The node's transaction nonce is out of sync with the chain. "
            "A prior transaction may be stuck or replaced."
        ),
        "REPLACEMENT_UNDERPRICED": (
            "A transaction replacement was attempted with insufficient gas bump. "
            "Network requires higher fee to replace pending tx."
        ),
        "INSUFFICIENT_FUNDS": (
            "Node wallet lacks sufficient native gas token to execute jobs. "
            "Review gas spend vs reward economics immediately."
        ),
    }

    explanation = runbooks.get(error_code, "Unknown error code. Manual investigation required.")

    return (
        f"Error: {error_code}\n"
        f"Context: {node_context}\n"
        f"Analysis: {explanation}\n"
        f"[This runbook is rule-based. With funding: Oracle 26AI vector search + semantic anomaly matching.]"
    )



async def generate_summary(client: httpx.AsyncClient, context: str, asset: str) -> str:
    system_instruction = (
        f"You are the AsyncSignals market intelligence engine. "
        f"Write a concise dashboard summary for {asset}. "
        f"Use 3-5 sentences. Focus on market structure, whale activity, price behavior, and relevant news. "
        f"Do not use hype, emojis, or markdown bullets. Be direct and analytical."
    )

    prompt = f"Create a summary for {asset} using this multi-chain market context:\n\n{context}"

    providers: list[tuple[str, Callable[..., Awaitable[str]]]] = [
        ("Groq", call_groq),
        ("Cerebras", call_cerebras),
        ("OpenRouter", call_openrouter),
        ("Gemini", call_gemini),
        ("Cloudflare", call_cloudflare),
    ]

    for name, fn in providers:
        try:
            print(f"Trying {name} for {asset} summary...")
            summary = await fn(client, prompt, system_instruction)
            if summary and summary.strip():
                return summary.strip()
        except Exception as e:
            print(f"{name} failed for {asset}: {sanitize_error_message(e)}")
        await asyncio.sleep(1.5)

    return build_rule_based_summary(context, asset)
    

def save_summaries(rows: list[dict]):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.executemany(
            """
            INSERT INTO ai_summaries (asset, summary, timestamp)
            VALUES (:1, :2, :3)
            """,
            [
                (
                    str(row["asset"]).upper()[:20],
                    str(row["summary"])[:4000],
                    str(row["timestamp"])[:50],
                )
                for row in rows
            ],
        )
        conn.commit()
        print(f"Inserted {len(rows)} summaries into ai_summaries")
    finally:
        cursor.close()
        conn.close()


async def main():
    print(f"[ASYNCLLM] started at {utc_now_str()} | DB_USER={DB_USER} | DSN={DB_DSN}")
    context = fetch_context_from_db()

    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
    timeout = httpx.Timeout(30.0, connect=15.0)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        btc_summary = await generate_summary(client, context, "BTC")
        sol_summary = await generate_summary(client, context, "SOL")
        dot_summary = await generate_summary(client, context, "DOT")
        base_summary = await generate_summary(client, context, "BASE")
        bnb_summary = await generate_summary(client, context, "BNB")
        sui_summary = await generate_summary(client, context, "SUI")
        nodeops_summary = await generate_summary(client, context, "NODEOPS")

    rows = [
        {"asset": "BTC", "summary": btc_summary, "timestamp": utc_now_str()},
        {"asset": "SOL", "summary": sol_summary, "timestamp": utc_now_str()},
        {"asset": "DOT", "summary": dot_summary, "timestamp": utc_now_str()},
        {"asset": "BASE", "summary": base_summary, "timestamp": utc_now_str()},
        {"asset": "BNB", "summary": bnb_summary, "timestamp": utc_now_str()},
        {"asset": "SUI", "summary": sui_summary, "timestamp": utc_now_str()},
        {"asset": "NODEOPS", "summary": nodeops_summary, "timestamp": utc_now_str()},
    ]

    save_summaries(rows)


if __name__ == "__main__":
    asyncio.run(main())
