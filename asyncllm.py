import asyncio
import os
from datetime import datetime, UTC
from typing import Callable, Awaitable

import httpx
import oracledb
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/data/.env")

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

        return (
            "=== PRICES ===\n"
            f"{prices_text}\n\n"
            "=== WHALES ===\n"
            f"{whales_text}\n\n"
            "=== NEWS ===\n"
            f"{news_text}"
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
            "model": "qwen3-coder",
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
            "model": "openrouter/free",
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
    return (
        f"{asset} summary is temporarily running on fallback mode. Core telemetry remains active even though "
        f"language-model providers are currently unavailable."
    )


async def generate_summary(client: httpx.AsyncClient, context: str, asset: str) -> str:
    system_instruction = (
        f"You are the AsyncSignals market intelligence engine. "
        f"Write a concise dashboard summary for {asset}. "
        f"Use 3-5 sentences. Focus on market structure, whale activity, price behavior, and relevant news. "
        f"Do not use hype, emojis, or markdown bullets. Be direct and analytical."
    )

    prompt = f"Create a summary for {asset} using this market context:\n\n{context}"

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

    rows = [
        {"asset": "BTC", "summary": btc_summary, "timestamp": utc_now_str()},
        {"asset": "SOL", "summary": sol_summary, "timestamp": utc_now_str()},
    ]

    save_summaries(rows)


if __name__ == "__main__":
    asyncio.run(main())