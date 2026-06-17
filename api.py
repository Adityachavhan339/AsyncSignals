import asyncio
import contextlib
import json
import os
import re
from datetime import date, datetime
from threading import Lock
from typing import Any, Dict, List, Optional
import httpx

import oracledb
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN", "asyncsignalsdatabase_high")
WALLET_DIR = os.getenv("WALLET_DIR", "/home/daniel/wallet")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

APP_TITLE = "AsyncSignals API"
APP_VERSION = "3.2.0"

DEFAULT_SIGNAL_LIMIT = 100
DEFAULT_WHALE_LIMIT = 50
DEFAULT_NEWS_LIMIT = 10
DEFAULT_MARKET_LIMIT = 25
DEFAULT_POLKADOT_LIMIT = 25
DEFAULT_POLKADOT_XCM_CACHE_LIMIT = 100
DEFAULT_POLKADOT_WHALE_MIN_USD = 0.0

AUTO_REFRESH_ENABLED = os.getenv("AUTO_REFRESH_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
AUTO_REFRESH_INTERVAL_SECONDS = max(30, int(os.getenv("AUTO_REFRESH_INTERVAL_SECONDS", "120")))
ENABLE_MANUAL_REFRESH = os.getenv("ENABLE_MANUAL_REFRESH", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
MANUAL_REFRESH_TOKEN = os.getenv("MANUAL_REFRESH_TOKEN")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
ALCHEMY_KEY = os.getenv("ALCHEMY_KEY")
SOLANA_DECODE_USE_AI = os.getenv("SOLANA_DECODE_USE_AI", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

POLKADOT_TABLES = [
    "POLKADOT_RPC_SNAPSHOT",
    "POLKADOT_CHAIN_ACTIVITY_DAILY",
    "POLKADOT_DERIVED_SIGNALS",
    "POLKADOT_EXTRINSIC_SUPPLEMENTARY_FEED",
    "POLKADOT_OPENGOV_SIGNALS",
    "POLKADOT_STAKING_DAILY",
    "POLKADOT_TREASURY_MONTHLY",
    "POLKADOT_VALIDATOR_MONTHLY",
    "POLKADOT_XCM_SUMMARY",
    "POLKADOT_XCM_TRANSFER_SIGNALS",
]

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=(
        "AsyncSignals B2B telemetry API with startup RAM cache, timed auto-refresh, "
        "shared asset endpoints, and dedicated Polkadot analytics routes."
    ),
)

allow_origins = [x.strip() for x in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins if allow_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE_LOCK = Lock()
CACHE: Dict[str, Any] = {
    "bundle": None,
    "loaded_at": None,
    "source": "startup_cache",
    "status": "empty",
    "error": None,
    "last_attempted_refresh_at": None,
    "auto_refresh_enabled": AUTO_REFRESH_ENABLED,
    "auto_refresh_interval_seconds": AUTO_REFRESH_INTERVAL_SECONDS,
}


def utc_now_z() -> str:
    return datetime.utcnow().isoformat() + "Z"


def get_connection():
    return oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        config_dir=WALLET_DIR,
        wallet_location=WALLET_DIR,
        wallet_password=DB_PASSWORD,
    )


def normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "read"):
        try:
            return value.read()
        except Exception:
            return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    return normalize_value(value)


def safe_limit(value: int, default_value: int, min_value: int = 1, max_value: int = 500) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default_value
    return max(min_value, min(parsed, max_value))


def fmt_usd(value: Any) -> str:
    try:
        if value in [None, "", "NaT"]:
            return "n/a"
        num = float(value)
        if abs(num) >= 1_000_000_000:
            return f"${num / 1_000_000_000:.2f}B"
        if abs(num) >= 1_000_000:
            return f"${num / 1_000_000:.2f}M"
        if abs(num) >= 1_000:
            return f"${num / 1_000:.2f}K"
        return f"${num:,.2f}"
    except Exception:
        return "n/a"


def short_addr(value: Any) -> str:
    text = str(value or "")
    if len(text) <= 14:
        return text
    return f"{text[:6]}...{text[-6:]}"


def run_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or {})
        columns = [col[0].lower() for col in cursor.description]
        rows = cursor.fetchall()
        return [{columns[i]: normalize_value(row[i]) for i in range(len(columns))} for row in rows]
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def run_scalar(query: str, params: Optional[Dict[str, Any]] = None) -> Any:
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or {})
        row = cursor.fetchone()
        return normalize_value(row[0]) if row else None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def table_exists(table_name: str) -> bool:
    count = run_scalar(
        """
        SELECT COUNT(*)
        FROM user_tables
        WHERE table_name = :table_name
        """,
        {"table_name": str(table_name).upper()},
    )
    return bool(count and int(count) > 0)


def fetch_prices(limit: int = DEFAULT_MARKET_LIMIT) -> List[Dict[str, Any]]:
    limit = safe_limit(limit, DEFAULT_MARKET_LIMIT, max_value=250)
    return run_query(
        f"""
        SELECT symbol, current_price, market_cap, price_change_percentage_24h
        FROM prices
        ORDER BY market_cap DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_paprika(limit: int = DEFAULT_MARKET_LIMIT) -> List[Dict[str, Any]]:
    limit = safe_limit(limit, DEFAULT_MARKET_LIMIT, max_value=250)
    return run_query(
        f"""
        SELECT symbol, name, price
        FROM paprika
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_whales(limit: int = DEFAULT_WHALE_LIMIT) -> List[Dict[str, Any]]:
    limit = safe_limit(limit, DEFAULT_WHALE_LIMIT, max_value=250)
    return run_query(
        f"""
        SELECT time, asset, amount, raw_qty, from_address, to_address
        FROM whales
        ORDER BY time DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_news(limit: int = DEFAULT_NEWS_LIMIT) -> List[Dict[str, Any]]:
    limit = safe_limit(limit, DEFAULT_NEWS_LIMIT, max_value=100)
    return run_query(
        f"""
        SELECT title, source_id, pubdate, description, link
        FROM news
        ORDER BY pubdate DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_signals(limit: int = DEFAULT_SIGNAL_LIMIT) -> List[Dict[str, Any]]:
    limit = safe_limit(limit, DEFAULT_SIGNAL_LIMIT, max_value=500)
    return run_query(
        f"""
        SELECT type, msg, timestamp, entry_price, exit_price, status
        FROM signals
        ORDER BY timestamp DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_latest_ai_summaries(asset: Optional[str] = None) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {}
    where_clause = ""
    if asset:
        where_clause = "WHERE UPPER(asset) = :asset"
        params["asset"] = asset.upper()

    return run_query(
        f"""
        SELECT asset, summary, timestamp
        FROM (
            SELECT
                asset,
                summary,
                timestamp,
                ROW_NUMBER() OVER (
                    PARTITION BY UPPER(asset)
                    ORDER BY timestamp DESC
                ) AS rn
            FROM ai_summaries
            {where_clause}
        )
        WHERE rn = 1
        ORDER BY timestamp DESC
        """,
        params,
    )


def build_market_snapshot(prices: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_symbol = {str(x.get("symbol", "")).upper(): x for x in prices}
    return {
        "btc": by_symbol.get("BTC"),
        "eth": by_symbol.get("ETH"),
        "sol": by_symbol.get("SOL"),
    }


def fetch_polkadot_rpc_snapshot() -> List[Dict[str, Any]]:
    if not table_exists("POLKADOT_RPC_SNAPSHOT"):
        return []
    return run_query(
        """
        SELECT
            captured_at,
            latest_block_number_hex,
            latest_block_number_int,
            latest_block_hash,
            finalized_head,
            extrinsics_in_latest_block
        FROM POLKADOT_RPC_SNAPSHOT
        ORDER BY captured_at DESC
        FETCH FIRST 1 ROWS ONLY
        """
    )


def fetch_polkadot_chain_activity(limit: int = 15) -> List[Dict[str, Any]]:
    if not table_exists("POLKADOT_CHAIN_ACTIVITY_DAILY"):
        return []
    limit = safe_limit(limit, 15, max_value=100)
    return run_query(
        f"""
        SELECT
            activity_date,
            relay_chain,
            chain_name,
            tx_count,
            tps,
            total_fees_native,
            total_fees_usd,
            total_fees_usd_30d,
            activity_score,
            alert_level
        FROM POLKADOT_CHAIN_ACTIVITY_DAILY
        WHERE activity_date = (
            SELECT MAX(activity_date)
            FROM POLKADOT_CHAIN_ACTIVITY_DAILY
        )
        ORDER BY activity_score DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_polkadot_derived_signals(limit: int = DEFAULT_POLKADOT_LIMIT) -> List[Dict[str, Any]]:
    if not table_exists("POLKADOT_DERIVED_SIGNALS"):
        return []
    limit = safe_limit(limit, DEFAULT_POLKADOT_LIMIT, max_value=200)
    return run_query(
        f"""
        SELECT
            signal_date,
            signal_family,
            signal_key,
            relay_chain,
            chain_name,
            severity,
            score,
            title,
            description,
            metric_value_1,
            metric_value_2,
            metric_value_3,
            reference_id
        FROM POLKADOT_DERIVED_SIGNALS
        ORDER BY signal_date DESC, score DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_polkadot_extrinsics(limit: int = 20) -> List[Dict[str, Any]]:
    if not table_exists("POLKADOT_EXTRINSIC_SUPPLEMENTARY_FEED"):
        return []
    limit = safe_limit(limit, 20, max_value=100)
    return run_query(
        f"""
        SELECT
            event_time,
            chain_name,
            block_number,
            extrinsic_hash,
            domain_name,
            pallet_name,
            method_name,
            signer_address,
            success_flag,
            summary_text
        FROM POLKADOT_EXTRINSIC_SUPPLEMENTARY_FEED
        ORDER BY event_time DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_polkadot_staking(limit: int = 15) -> List[Dict[str, Any]]:
    if not table_exists("POLKADOT_STAKING_DAILY"):
        return []
    limit = safe_limit(limit, 15, max_value=100)
    return run_query(
        f"""
        SELECT
            staking_date,
            relay_chain,
            chain_name,
            minimum_nominator_active_stake,
            number_of_addresses_staking,
            number_of_nominators,
            number_of_pool_members,
            number_of_pools,
            number_of_validators,
            staked_dot,
            staked_dot_in_pools,
            unbonding_dot
        FROM POLKADOT_STAKING_DAILY
        ORDER BY staking_date DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_polkadot_treasury(limit: int = 12) -> List[Dict[str, Any]]:
    if not table_exists("POLKADOT_TREASURY_MONTHLY"):
        return []
    limit = safe_limit(limit, 12, max_value=100)
    return run_query(
        f"""
        SELECT
            month_date,
            relay_chain,
            chain_name,
            asset_symbol,
            balance_token,
            balance_usd,
            treasury_share_pct
        FROM POLKADOT_TREASURY_MONTHLY
        ORDER BY month_date DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_polkadot_validators(limit: int = 6) -> List[Dict[str, Any]]:
    if not table_exists("POLKADOT_VALIDATOR_MONTHLY"):
        return []
    limit = safe_limit(limit, 6, max_value=50)
    return run_query(
        f"""
        SELECT
            month_date,
            relay_chain,
            chain_name,
            number_of_nominators,
            number_of_active_validators,
            number_of_waiting_validators,
            waiting_ratio_pct
        FROM POLKADOT_VALIDATOR_MONTHLY
        ORDER BY month_date DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_polkadot_xcm_summary(limit: int = 5) -> List[Dict[str, Any]]:
    if not table_exists("POLKADOT_XCM_SUMMARY"):
        return []
    limit = safe_limit(limit, 5, max_value=50)
    return run_query(
        f"""
        SELECT
            relay_chain,
            window_hours,
            total_messages,
            completed_messages,
            failed_messages,
            matched_messages,
            success_rate,
            avg_latency_seconds,
            median_latency_seconds,
            p95_latency_seconds,
            unmatched_messages
        FROM POLKADOT_XCM_SUMMARY
        ORDER BY window_hours DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_polkadot_xcm_transfers(limit: int = DEFAULT_POLKADOT_XCM_CACHE_LIMIT) -> List[Dict[str, Any]]:
    if not table_exists("POLKADOT_XCM_TRANSFER_SIGNALS"):
        return []
    limit = safe_limit(limit, DEFAULT_POLKADOT_XCM_CACHE_LIMIT, max_value=200)
    return run_query(
        f"""
        SELECT
            origin_timestamp,
            relay_chain,
            origin_chain,
            dest_chain,
            origin_para_id,
            dest_para_id,
            xcm_type,
            xcm_version,
            message_hash,
            message_id,
            origin_account,
            dest_account,
            asset_symbol,
            value_usd,
            origin_block_number,
            outcome_status,
            match_status,
            latency_seconds,
            route_status,
            signal_score
        FROM POLKADOT_XCM_TRANSFER_SIGNALS
        ORDER BY origin_timestamp DESC, signal_score DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_polkadot_opengov(limit: int = 10) -> List[Dict[str, Any]]:
    if not table_exists("POLKADOT_OPENGOV_SIGNALS"):
        return []
    limit = safe_limit(limit, 10, max_value=100)
    return run_query(
        f"""
        SELECT
            start_date,
            end_date,
            relay_chain,
            chain_name,
            referendum_index,
            origin_name,
            track_id,
            outcome_status,
            ayes,
            nays,
            support_value,
            turnout_total,
            approval_margin,
            urgency_score,
            signal_label
        FROM POLKADOT_OPENGOV_SIGNALS
        ORDER BY start_date DESC, urgency_score DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def row_sort_value(value: Any) -> float:
    try:
        if value in [None, "", "NaT"]:
            return -1.0
        return float(value)
    except Exception:
        return -1.0


def count_rows_with_value_usd(rows: List[Dict[str, Any]]) -> int:
    return len([x for x in rows if x.get("value_usd") not in [None, "", "NaT"]])


def count_rows_without_value_usd(rows: List[Dict[str, Any]]) -> int:
    return len([x for x in rows if x.get("value_usd") in [None, "", "NaT"]])


def filter_polkadot_whales_from_rows(
    rows: List[Dict[str, Any]],
    asset_symbol: Optional[str] = None,
    min_usd: float = DEFAULT_POLKADOT_WHALE_MIN_USD,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    for row in rows:
        symbol = str(row.get("asset_symbol", "")).upper()
        raw_value_usd = row.get("value_usd")

        if asset_symbol and symbol != asset_symbol.upper():
            continue

        if raw_value_usd in [None, "", "NaT"]:
            if float(min_usd) > 0:
                continue
            value_usd = None
        else:
            try:
                value_usd = float(raw_value_usd)
            except Exception:
                if float(min_usd) > 0:
                    continue
                value_usd = None

        if value_usd is not None and value_usd < float(min_usd):
            continue

        out.append(row)

    out.sort(
        key=lambda x: (
            row_sort_value(x.get("value_usd")),
            str(x.get("origin_timestamp", "")),
        ),
        reverse=True,
    )
    return out


def fetch_polkadot_data(
    derived_limit: int = DEFAULT_POLKADOT_LIMIT,
    xcm_transfer_limit: int = DEFAULT_POLKADOT_XCM_CACHE_LIMIT,
) -> Dict[str, Any]:
    available = any(table_exists(name) for name in POLKADOT_TABLES)
    return {
        "available": available,
        "rpc_snapshot": fetch_polkadot_rpc_snapshot(),
        "chain_activity": fetch_polkadot_chain_activity(),
        "derived_signals": fetch_polkadot_derived_signals(limit=derived_limit),
        "extrinsic_feed": fetch_polkadot_extrinsics(),
        "staking": fetch_polkadot_staking(),
        "treasury": fetch_polkadot_treasury(),
        "validators": fetch_polkadot_validators(),
        "xcm_summary": fetch_polkadot_xcm_summary(),
        "xcm_transfers": fetch_polkadot_xcm_transfers(limit=xcm_transfer_limit),
        "opengov": fetch_polkadot_opengov(),
    }


def build_bundle() -> Dict[str, Any]:
    prices = fetch_prices()
    paprika = fetch_paprika()
    whales = fetch_whales()
    news = fetch_news()
    signals = fetch_signals()
    summaries = fetch_latest_ai_summaries()
    polkadot = fetch_polkadot_data(
        derived_limit=DEFAULT_POLKADOT_LIMIT,
        xcm_transfer_limit=DEFAULT_POLKADOT_XCM_CACHE_LIMIT,
    )

    latest_signal = signals[0] if signals else None
    total_whale_usd = sum(float(x.get("raw_qty") or 0) for x in whales)
    sol_whale_usd = sum(
        float(x.get("raw_qty") or 0)
        for x in whales
        if str(x.get("asset", "")).upper() == "SOL"
    )

    polkadot_xcm_rows = filter_polkadot_whales_from_rows(
        polkadot.get("xcm_transfers", []),
        min_usd=DEFAULT_POLKADOT_WHALE_MIN_USD,
    )
    polkadot_xcm_usd = sum(
        float(x.get("value_usd") or 0)
        for x in polkadot_xcm_rows
        if x.get("value_usd") not in [None, "", "NaT"]
    )

    return {
        "meta": {
            "service": "AsyncSignals",
            "version": APP_VERSION,
            "generated_at": utc_now_z(),
            "mode": "b2b_data_provider_cached",
            "counts": {
                "prices": len(prices),
                "paprika": len(paprika),
                "whales": len(whales),
                "news": len(news),
                "signals": len(signals),
                "summaries": len(summaries),
                "polkadot_chain_activity": len(polkadot.get("chain_activity", [])),
                "polkadot_derived_signals": len(polkadot.get("derived_signals", [])),
                "polkadot_extrinsic_feed": len(polkadot.get("extrinsic_feed", [])),
                "polkadot_xcm_transfers": len(polkadot.get("xcm_transfers", [])),
                "polkadot_whales": len(polkadot_xcm_rows),
            },
        },
        "highlights": {
            "latest_signal": latest_signal,
            "total_whale_usd": total_whale_usd,
            "sol_whale_usd": sol_whale_usd,
            "polkadot_whale_usd": polkadot_xcm_usd,
            "market_snapshot": build_market_snapshot(prices),
        },
        "summaries": summaries,
        "signals": signals,
        "market": prices,
        "market_reference": paprika,
        "whales": whales,
        "news": news,
        "polkadot": polkadot,
    }


def render_summaries_text(rows: List[Dict[str, Any]]) -> str:
    lines = ["ASYNC SIGNALS :: SUMMARIES", ""]
    if not rows:
        return "ASYNC SIGNALS :: SUMMARIES\n\nNo summary rows found."
    for row in rows:
        lines.append(f"ASSET: {row.get('asset', '-')}")
        lines.append(f"UPDATED: {row.get('timestamp', '-')}")
        lines.append(str(row.get("summary", "")).strip())
        lines.append("-" * 80)
    return "\n".join(lines)


def render_signals_text(rows: List[Dict[str, Any]]) -> str:
    lines = ["ASYNC SIGNALS :: SIGNALS", ""]
    if not rows:
        return "ASYNC SIGNALS :: SIGNALS\n\nNo signal rows found."
    for row in rows:
        lines.append(f"{row.get('timestamp', '-')} | {row.get('type', '-')}")
        lines.append(f"STATUS: {row.get('status', '-')}")
        lines.append(f"ENTRY: {fmt_usd(row.get('entry_price'))} | EXIT: {fmt_usd(row.get('exit_price'))}")
        lines.append(str(row.get("msg", "")).strip())
        lines.append("-" * 80)
    return "\n".join(lines)


def render_shared_whales_text(rows: List[Dict[str, Any]]) -> str:
    lines = ["ASYNC SIGNALS :: WHALES", ""]
    if not rows:
        return "ASYNC SIGNALS :: WHALES\n\nNo whale rows found."
    for row in rows:
        lines.append(
            f"{row.get('time', '-')} | {row.get('asset', '-')} | "
            f"amount={row.get('amount', 0)} | usd={fmt_usd(row.get('raw_qty'))}"
        )
        lines.append(f"{short_addr(row.get('from_address'))} -> {short_addr(row.get('to_address'))}")
        lines.append("-" * 80)
    return "\n".join(lines)


def render_polkadot_whales_text(rows: List[Dict[str, Any]]) -> str:
    lines = ["ASYNC SIGNALS :: POLKADOT XCM TRANSFERS", ""]
    if not rows:
        return "ASYNC SIGNALS :: POLKADOT XCM TRANSFERS\n\nNo Polkadot XCM transfer rows found."
    for row in rows:
        lines.append(
            f"{row.get('origin_timestamp', '-')} | {row.get('asset_symbol', '-')} | "
            f"usd={fmt_usd(row.get('value_usd'))} | score={row.get('signal_score', '-')}"
        )
        lines.append(
            f"{row.get('origin_chain', '-')} -> {row.get('dest_chain', '-')} | "
            f"{short_addr(row.get('origin_account'))} -> {short_addr(row.get('dest_account'))}"
        )
        lines.append(
            f"status={row.get('outcome_status', '-')} | "
            f"match={row.get('match_status', '-')} | route={row.get('route_status', '-')}"
        )
        lines.append("-" * 80)
    return "\n".join(lines)


def render_bundle_text(bundle: Dict[str, Any]) -> str:
    lines = ["ASYNC SIGNALS :: SNAPSHOT", ""]
    meta = bundle.get("meta", {})
    counts = meta.get("counts", {})
    highlights = bundle.get("highlights", {})
    latest_signal = highlights.get("latest_signal") or {}
    market_snapshot = highlights.get("market_snapshot") or {}

    lines.append(f"GENERATED AT: {meta.get('generated_at', '-')}")
    lines.append(f"SERVICE: {meta.get('service', '-')}")
    lines.append(f"MODE: {meta.get('mode', '-')}")
    lines.append("")

    lines.append("COUNTS")
    for k, v in counts.items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("MARKET SNAPSHOT")
    for symbol in ["btc", "eth", "sol"]:
        row = market_snapshot.get(symbol)
        if row:
            lines.append(
                f"- {str(row.get('symbol', '')).upper()}: {fmt_usd(row.get('current_price'))} | "
                f"market cap {fmt_usd(row.get('market_cap'))} | "
                f"24h {row.get('price_change_percentage_24h', 0)}%"
            )
    lines.append("")

    lines.append("WHALE FLOW")
    lines.append(f"- total tracked whale USD: {fmt_usd(highlights.get('total_whale_usd'))}")
    lines.append(f"- SOL whale USD: {fmt_usd(highlights.get('sol_whale_usd'))}")
    lines.append(f"- Polkadot XCM USD: {fmt_usd(highlights.get('polkadot_whale_usd'))}")
    lines.append("")

    lines.append("LATEST SIGNAL")
    if latest_signal:
        lines.append(f"- {latest_signal.get('timestamp', '-')} | {latest_signal.get('type', '-')}")
        lines.append(f"- {latest_signal.get('msg', '-')}")
        lines.append(f"- status: {latest_signal.get('status', '-')}")
    else:
        lines.append("- No signal rows found.")
    lines.append("")

    lines.append("AI SUMMARIES")
    summaries = bundle.get("summaries", [])
    if summaries:
        for row in summaries:
            lines.append(f"[{row.get('asset', '-')}] {row.get('timestamp', '-')}")
            lines.append(str(row.get("summary", "")).strip())
            lines.append("")
    else:
        lines.append("No AI summaries found.")
        lines.append("")

    lines.append("RECENT WHALES")
    whales = bundle.get("whales", [])[:10]
    if whales:
        for row in whales:
            lines.append(
                f"- {row.get('time', '-')} | {row.get('asset', '-')} | amount={row.get('amount', 0)} | "
                f"usd={fmt_usd(row.get('raw_qty'))} | "
                f"{short_addr(row.get('from_address'))} -> {short_addr(row.get('to_address'))}"
            )
    else:
        lines.append("- No whale rows found.")
    lines.append("")

    polkadot = bundle.get("polkadot", {})
    if polkadot.get("available"):
        lines.append("POLKADOT")

        rpc_rows = polkadot.get("rpc_snapshot", [])
        if rpc_rows:
            rpc = rpc_rows[0]
            lines.append(
                f"- block {rpc.get('latest_block_number_int', '-')} | "
                f"extrinsics in latest block: {rpc.get('extrinsics_in_latest_block', '-')}"
            )

        activity_rows = polkadot.get("chain_activity", [])[:5]
        if activity_rows:
            lines.append("- chain activity leaders:")
            for row in activity_rows:
                lines.append(
                    f" • {row.get('activity_date', '-')} | {row.get('chain_name', '-')} | "
                    f"tx={row.get('tx_count', 0)} | tps={row.get('tps', 0)} | "
                    f"score={row.get('activity_score', 0)}"
                )

        xcm_rows = filter_polkadot_whales_from_rows(
            polkadot.get("xcm_transfers", []),
            min_usd=DEFAULT_POLKADOT_WHALE_MIN_USD,
        )[:5]
        if xcm_rows:
            lines.append("- top polkadot xcm routes:")
            for row in xcm_rows:
                lines.append(
                    f" • {row.get('asset_symbol', '-')} | usd={fmt_usd(row.get('value_usd'))} | "
                    f"{row.get('origin_chain', '-')} -> {row.get('dest_chain', '-')} | "
                    f"route={row.get('route_status', '-')}"
                )

        derived = polkadot.get("derived_signals", [])[:8]
        if derived:
            lines.append("- top derived signals:")
            for row in derived:
                lines.append(
                    f" • {row.get('signal_date', '-')} | {row.get('signal_family', '-')} | "
                    f"{row.get('chain_name', '-')} | {row.get('severity', '-')} | "
                    f"{row.get('title', '-')}"
                )

    return "\n".join(lines).strip()


def respond(payload: Dict[str, Any], output_format: str, text_renderer):
    if output_format == "text":
        items = payload["items"] if "items" in payload else payload
        return PlainTextResponse(text_renderer(items))
    return JSONResponse(content=to_jsonable(payload))


def clone_cached_bundle() -> Dict[str, Any]:
    with CACHE_LOCK:
        bundle = CACHE.get("bundle")
        if not bundle:
            raise HTTPException(status_code=503, detail="Cache not loaded")
        return to_jsonable(bundle)


def get_cache_meta() -> Dict[str, Any]:
    with CACHE_LOCK:
        return {
            "cache_loaded_at": CACHE.get("loaded_at"),
            "cache_status": CACHE.get("status"),
            "cache_source": CACHE.get("source"),
            "cache_error": CACHE.get("error"),
            "last_attempted_refresh_at": CACHE.get("last_attempted_refresh_at"),
            "auto_refresh_enabled": CACHE.get("auto_refresh_enabled"),
            "auto_refresh_interval_seconds": CACHE.get("auto_refresh_interval_seconds"),
        }


def load_cache(source: str = "manual_refresh") -> Dict[str, Any]:
    attempted_at = utc_now_z()
    with CACHE_LOCK:
        CACHE["last_attempted_refresh_at"] = attempted_at
        if CACHE.get("bundle") is not None:
            CACHE["status"] = "refreshing"

    try:
        bundle = build_bundle()
        loaded_at = utc_now_z()
        with CACHE_LOCK:
            CACHE["bundle"] = bundle
            CACHE["loaded_at"] = loaded_at
            CACHE["source"] = source
            CACHE["status"] = "ready"
            CACHE["error"] = None
        return get_cache_meta()
    except Exception as exc:
        with CACHE_LOCK:
            CACHE["source"] = source
            CACHE["error"] = str(exc)
            CACHE["status"] = "error" if CACHE.get("bundle") is None else "stale"
        if CACHE.get("bundle") is None:
            raise
        return get_cache_meta()


def cached_bundle_with_meta() -> Dict[str, Any]:
    bundle = clone_cached_bundle()
    bundle_meta = bundle.get("meta", {})
    bundle_meta.update(get_cache_meta())
    bundle["meta"] = bundle_meta
    return bundle


def get_cached_section(section_name: str, default: Any):
    bundle = clone_cached_bundle()
    return bundle.get(section_name, default)


def get_cached_polkadot() -> Dict[str, Any]:
    bundle = clone_cached_bundle()
    return bundle.get("polkadot", {"available": False})

class SolanaDecodeRequest(BaseModel):
    input_type: Optional[str] = Field(default="auto")
    payload: Any = None
    signature: Optional[str] = None
    program_id: Optional[str] = None
    logs: Optional[List[str]] = None
    transaction: Optional[Dict[str, Any]] = None
    accounts: Optional[List[str]] = None
    use_ai: bool = Field(default=False)


def stringify_payload(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    try:
        return json.dumps(payload, ensure_ascii=False)
    except Exception:
        return str(payload)


def extract_logs(payload: Any, explicit_logs: Optional[List[str]] = None) -> List[str]:
    if explicit_logs:
        return [str(x) for x in explicit_logs]

    if isinstance(payload, dict):
        logs = payload.get("logs")
        if isinstance(logs, list):
            return [str(x) for x in logs]
        value = payload.get("value")
        if isinstance(value, dict):
            inner_logs = value.get("logs")
            if isinstance(inner_logs, list):
                return [str(x) for x in inner_logs]
    return []


def classify_solana_input(input_type: Optional[str], payload: Any) -> str:
    if input_type and str(input_type).lower() not in {"", "auto"}:
        return str(input_type).lower()

    text = stringify_payload(payload).lower()

    if isinstance(payload, dict) and ("err" in payload or "logs" in payload or "value" in payload):
        return "simulation_failure"

    if "anchorerror" in text or "error code:" in text or re.search(r"0x[0-9a-f]+", text):
        return "anchor_error"

    return "runtime_log"


def build_decode_result(
    error_class: str,
    label: str,
    summary: str,
    root_cause: str,
    remediation: List[str],
    matched_signals: List[str],
    input_kind: str,
    raw_excerpt: str,
) -> Dict[str, Any]:
    return {
        "ok": True,
        "input_kind": input_kind,
        "error_class": error_class,
        "label": label,
        "summary": summary,
        "root_cause": root_cause,
        "remediation": remediation,
        "matched_signals": matched_signals,
        "raw_excerpt": raw_excerpt[:500],
    }


def decode_runtime_text(text: str) -> Dict[str, Any]:
    lower = text.lower()
    matched: List[str] = []

    if "compute budget exceeded" in lower or "computational budget exceeded" in lower or ("consumed" in lower and "compute units" in lower):
        matched.append("compute_budget")
        return build_decode_result(
            error_class="runtime_execution_error",
            label="ComputeBudgetExceeded",
            summary="The transaction ran out of compute units during execution.",
            root_cause="One or more instructions consumed more compute than the transaction budget allowed.",
            remediation=[
                "Reduce instruction complexity or split work across transactions.",
                "Add a compute budget instruction if your client supports it.",
                "Check which instruction is producing the largest log expansion or CPI depth.",
            ],
            matched_signals=matched,
            input_kind="runtime_log",
            raw_excerpt=text,
        )

    if "blockhash not found" in lower or "transaction expired" in lower or "expired blockhash" in lower:
        matched.append("blockhash")
        return build_decode_result(
            error_class="runtime_execution_error",
            label="BlockhashExpired",
            summary="The transaction used an expired or missing recent blockhash.",
            root_cause="The transaction was signed too early, sent too late, or retried with a stale blockhash.",
            remediation=[
                "Fetch a fresh recent blockhash before signing.",
                "Avoid long delays between signing and submission.",
                "Rebuild and resend the transaction with updated blockhash data.",
            ],
            matched_signals=matched,
            input_kind="runtime_log",
            raw_excerpt=text,
        )

    if "insufficient funds" in lower:
        matched.append("balance")
        return build_decode_result(
            error_class="runtime_execution_error",
            label="InsufficientFunds",
            summary="The payer or source account does not have enough balance.",
            root_cause="The transaction requires more SOL or token balance than the signing account currently holds.",
            remediation=[
                "Check SOL balance for fees and rent.",
                "Check token account balance for the asset being moved.",
                "Verify the correct payer and source accounts are being used.",
            ],
            matched_signals=matched,
            input_kind="runtime_log",
            raw_excerpt=text,
        )

    if "signature verification failed" in lower or "missing required signature" in lower:
        matched.append("signature")
        return build_decode_result(
            error_class="runtime_execution_error",
            label="SignatureVerificationFailed",
            summary="A required signer was missing or did not sign correctly.",
            root_cause="The transaction expects a signer that was omitted, mismatched, or not authorized properly.",
            remediation=[
                "Confirm all required signers are included.",
                "Verify the wallet or keypair is signing the exact transaction message.",
                "Check account ordering and signer flags in the client code.",
            ],
            matched_signals=matched,
            input_kind="runtime_log",
            raw_excerpt=text,
        )

    if "account not found" in lower or "could not find account" in lower or "invalid account data" in lower:
        matched.append("account_state")
        return build_decode_result(
            error_class="runtime_execution_error",
            label="AccountStateError",
            summary="The transaction referenced an account that was missing or had invalid state/data.",
            root_cause="An expected account may not exist, may be the wrong address, or may not match the expected program layout.",
            remediation=[
                "Verify every account address passed into the instruction.",
                "Check that the account is initialized and owned by the expected program.",
                "Confirm the client is using the correct PDA seeds and account order.",
            ],
            matched_signals=matched,
            input_kind="runtime_log",
            raw_excerpt=text,
        )

    return build_decode_result(
        error_class="runtime_execution_error",
        label="UnknownRuntimeError",
        summary="The runtime failure did not match a known high-confidence pattern.",
        root_cause="The logs indicate execution failed, but the exact cause needs deeper inspection.",
        remediation=[
            "Review the failing instruction index and surrounding logs.",
            "Compare the account list, signer set, and recent blockhash handling.",
            "Re-run simulation with verbose logs for more detail.",
        ],
        matched_signals=matched,
        input_kind="runtime_log",
        raw_excerpt=text,
    )


def decode_anchor_text(text: str) -> Dict[str, Any]:
    matched: List[str] = []
    lower = text.lower()

    code_match = re.search(r"error code:\s*([A-Za-z0-9_]+)", text, re.IGNORECASE)
    number_match = re.search(r"error number:\s*(\d+)", text, re.IGNORECASE)
    hex_match = re.search(r"0x[0-9a-fA-F]+", text)

    label = code_match.group(1) if code_match else "AnchorCustomError"
    anchor_number = number_match.group(1) if number_match else None
    anchor_hex = hex_match.group(0) if hex_match else None

    if "constraintsigner" in lower:
        matched.append("constraint_signer")
        return build_decode_result(
            error_class="anchor_constraint_error",
            label="ConstraintSigner",
            summary="An Anchor signer constraint failed.",
            root_cause="An account expected to sign the instruction was missing or did not sign.",
            remediation=[
                "Confirm the required signer is included in the transaction.",
                "Verify the correct wallet or keypair signs the instruction.",
                "Check the client account order and signer metadata.",
            ],
            matched_signals=matched,
            input_kind="anchor_error",
            raw_excerpt=text,
        )

    if "constrainthasone" in lower:
        matched.append("constraint_has_one")
        return build_decode_result(
            error_class="anchor_constraint_error",
            label="ConstraintHasOne",
            summary="An Anchor has_one relationship check failed.",
            root_cause="The account data does not point to the expected related authority or linked account.",
            remediation=[
                "Check the account field referenced by has_one in the program.",
                "Verify the authority or related account passed by the client matches on-chain state.",
                "Inspect whether the wrong PDA or stale account was supplied.",
            ],
            matched_signals=matched,
            input_kind="anchor_error",
            raw_excerpt=text,
        )

    if "constraint" in lower:
        matched.append("generic_anchor_constraint")
        return build_decode_result(
            error_class="anchor_constraint_error",
            label=label,
            summary="An Anchor account constraint failed during instruction validation.",
            root_cause="The program rejected one of the provided accounts before full execution.",
            remediation=[
                "Compare the account list against the program instruction definition.",
                "Check signer, mutability, PDA seed, and authority expectations.",
                "Inspect the exact constraint label and account named in the logs.",
            ],
            matched_signals=matched,
            input_kind="anchor_error",
            raw_excerpt=text,
        )

    suffix = ""
    if anchor_number:
        suffix += f" Anchor error number: {anchor_number}."
    if anchor_hex:
        suffix += f" Raw hex code: {anchor_hex}."

    return build_decode_result(
        error_class="anchor_custom_error",
        label=label,
        summary="A custom Anchor program error was detected.",
        root_cause="The program returned a custom error that may require IDL or program-specific mapping for deeper decoding.",
        remediation=[
            "Check program logs for account names and validation hints.",
            "Look up the custom error in the Anchor program source or IDL if available.",
            "Pair the raw code with simulation logs to identify the failing instruction context.",
        ],
        matched_signals=matched,
        input_kind="anchor_error",
        raw_excerpt=(text + suffix),
    )


def decode_simulation_payload(payload: Any) -> Dict[str, Any]:
    logs = extract_logs(payload)
    text = "\n".join(logs) if logs else stringify_payload(payload)
    lower = text.lower()
    matched: List[str] = []

    if "constraintsigner" in lower or "anchorerror" in lower:
        return decode_anchor_text(text)

    if "instructionerror" in lower:
        matched.append("instruction_error")

    if "missing required signature" in lower or "signature verification failed" in lower:
        matched.append("signature")
        return build_decode_result(
            error_class="rpc_simulation_failure",
            label="SignatureMismatch",
            summary="Simulation failed because a required signature was missing or invalid.",
            root_cause="The transaction message expected one or more valid signers that were not present.",
            remediation=[
                "Verify all expected signers are attached before simulation or send.",
                "Check wallet adapter or signing flow for partial-sign behavior.",
                "Confirm the payer and authority accounts match the instruction requirements.",
            ],
            matched_signals=matched,
            input_kind="simulation_failure",
            raw_excerpt=text,
        )

    if "account" in lower and ("not found" in lower or "invalid" in lower or "missing" in lower):
        matched.append("account_layout")
        return build_decode_result(
            error_class="rpc_simulation_failure",
            label="AccountLayoutOrMissingAccount",
            summary="Simulation failed because one or more accounts were missing or structurally incorrect.",
            root_cause="The RPC preflight step could not validate the account set required by the instruction.",
            remediation=[
                "Check that all accounts are present and in the expected order.",
                "Verify PDAs, token accounts, and ownership assumptions.",
                "Compare the simulated accounts against the program instruction schema.",
            ],
            matched_signals=matched,
            input_kind="simulation_failure",
            raw_excerpt=text,
        )

    return build_decode_result(
        error_class="rpc_simulation_failure",
        label="GenericSimulationFailure",
        summary="The transaction failed during RPC simulation or preflight checks.",
        root_cause="The payload indicates the instruction set could not pass preflight validation, but the exact cause needs deeper log inspection.",
        remediation=[
            "Inspect the failing instruction index and log sequence.",
            "Re-run simulation with complete logs enabled.",
            "Check account ordering, signer flags, and transaction assembly.",
        ],
        matched_signals=matched,
        input_kind="simulation_failure",
        raw_excerpt=text,
    )


def decode_solana_error_payload(input_type: Optional[str], payload: Any) -> Dict[str, Any]:
    kind = classify_solana_input(input_type, payload)

    if kind == "anchor_error":
        return decode_anchor_text(stringify_payload(payload))

    if kind == "simulation_failure":
        return decode_simulation_payload(payload)

    return decode_runtime_text(stringify_payload(payload))

def sanitize_ai_error_message(err: Exception) -> str:
    msg = str(err)
    secrets = [
        GROQ_API_KEY,
        OPENROUTER_API_KEY,
        GEMINI_API_KEY,
        CEREBRAS_API_KEY,
        CLOUDFLARE_API_TOKEN,
        CLOUDFLARE_ACCOUNT_ID,
    ]
    for secret in secrets:
        if secret:
            msg = msg.replace(secret, "[REDACTED]")
    return msg


async def ai_call_groq(client: httpx.AsyncClient, prompt: str, system_instruction: str) -> str:
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


async def ai_call_openrouter(client: httpx.AsyncClient, prompt: str, system_instruction: str) -> str:
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


async def ai_call_gemini(client: httpx.AsyncClient, prompt: str, system_instruction: str) -> str:
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


async def ai_call_cerebras(client: httpx.AsyncClient, prompt: str, system_instruction: str) -> str:
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


async def ai_call_cloudflare(client: httpx.AsyncClient, prompt: str, system_instruction: str) -> str:
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


def build_ai_decoder_prompt(decoded: Dict[str, Any], request: SolanaDecodeRequest) -> str:
    return json.dumps(
        {
            "input_type": request.input_type,
            "signature": request.signature,
            "program_id": request.program_id,
            "accounts": request.accounts,
            "transaction": request.transaction,
            "logs": request.logs,
            "decoded_result": decoded,
            "original_payload_excerpt": stringify_payload(request.payload)[:1500],
        },
        ensure_ascii=False,
        indent=2,
    )


async def generate_ai_decoder_explanation(decoded: Dict[str, Any], request: SolanaDecodeRequest) -> Dict[str, Any]:
    system_instruction = (
        "You are the AsyncSignals Solana debugging assistant. "
        "Given a deterministic decoder result and the original input, produce a concise JSON object "
        "with keys: explanation, likely_fix, confidence, next_checks. "
        "confidence must be one of: high, medium, low. "
        "next_checks must be a JSON array of short strings. "
        "Do not use markdown. Do not include code fences."
    )

    prompt = build_ai_decoder_prompt(decoded, request)

    providers = [
        ("Groq", ai_call_groq),
        ("Cerebras", ai_call_cerebras),
        ("OpenRouter", ai_call_openrouter),
        ("Gemini", ai_call_gemini),
        ("Cloudflare", ai_call_cloudflare),
    ]

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(30.0, connect=15.0)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        last_error = None

        for provider_name, fn in providers:
            try:
                text = await fn(client, prompt, system_instruction)
                parsed = json.loads(text)

                return {
                    "provider": provider_name,
                    "explanation": str(parsed.get("explanation", "")).strip(),
                    "likely_fix": str(parsed.get("likely_fix", "")).strip(),
                    "confidence": str(parsed.get("confidence", "medium")).strip().lower(),
                    "next_checks": parsed.get("next_checks", []),
                }
            except Exception as exc:
                last_error = sanitize_ai_error_message(exc)

    return {
        "provider": None,
        "explanation": "",
        "likely_fix": "",
        "confidence": "low",
        "next_checks": [],
        "error": last_error or "No AI provider succeeded",
    }

def filter_summaries_by_asset(asset: str) -> List[Dict[str, Any]]:
    items = get_cached_section("summaries", [])
    return [x for x in items if str(x.get("asset", "")).upper() == asset.upper()]


def filter_signals_by_type(signal_type: str) -> List[Dict[str, Any]]:
    items = get_cached_section("signals", [])
    return [x for x in items if str(x.get("type", "")).upper() == signal_type.upper()]


def filter_shared_whales_by_asset(asset: str) -> List[Dict[str, Any]]:
    items = get_cached_section("whales", [])
    return [x for x in items if str(x.get("asset", "")).upper() == asset.upper()]


def filter_polkadot_whales(
    asset_symbol: Optional[str] = None,
    min_usd: float = DEFAULT_POLKADOT_WHALE_MIN_USD,
) -> List[Dict[str, Any]]:
    polkadot = get_cached_polkadot()
    items = polkadot.get("xcm_transfers", [])
    return filter_polkadot_whales_from_rows(items, asset_symbol=asset_symbol, min_usd=min_usd)


async def auto_refresh_loop():
    while True:
        await asyncio.sleep(AUTO_REFRESH_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(load_cache, "auto_refresh")
        except Exception:
            pass


@app.on_event("startup")
async def startup_load_cache():
    await asyncio.to_thread(load_cache, "startup")
    if AUTO_REFRESH_ENABLED:
        app.state.auto_refresh_task = asyncio.create_task(auto_refresh_loop())
    else:
        app.state.auto_refresh_task = None


@app.on_event("shutdown")
async def shutdown_event():
    task = getattr(app.state, "auto_refresh_task", None)
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@app.get("/")
def root():
    endpoints = [
        "/health",
        "/market",
        "/news",
        "/whales",
        "/whales/{asset}",
        "/summaries",
        "/summaries/{asset}",
        "/signals",
        "/signals/{signal_type}",
        "/polkadot",
        "/polkadot/whales",
        "/polkadot/whales/{asset_symbol}",
        "/base",
        "/base/whales",
        "/base/signals",
        "/bundle",
    ]

    if ENABLE_MANUAL_REFRESH:
        endpoints.append("/refresh")

    return {
        "service": APP_TITLE,
        "version": APP_VERSION,
        "mode": "startup_ram_cache_with_auto_refresh",
        "endpoints": endpoints,
        "formats": ["json", "text"],
        "auto_refresh_enabled": AUTO_REFRESH_ENABLED,
        "auto_refresh_interval_seconds": AUTO_REFRESH_INTERVAL_SECONDS,
        "manual_refresh_enabled": ENABLE_MANUAL_REFRESH,
    }


@app.get("/health")
def health():
    meta = get_cache_meta()
    return {
        "service": APP_TITLE,
        "version": APP_VERSION,
        "ok": CACHE.get("bundle") is not None,
        "timestamp": utc_now_z(),
        **meta,
        "manual_refresh_enabled": ENABLE_MANUAL_REFRESH,
    }


@app.post("/refresh")
async def refresh_cache(x_refresh_token: Optional[str] = Header(None)):
    if not ENABLE_MANUAL_REFRESH:
        raise HTTPException(status_code=403, detail="Manual refresh is disabled")
    if MANUAL_REFRESH_TOKEN and x_refresh_token != MANUAL_REFRESH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    try:
        meta = await asyncio.to_thread(load_cache, "manual_refresh")
        return {
            "ok": True,
            "message": "Cache refreshed successfully",
            "timestamp": utc_now_z(),
            **meta,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {exc}")

@app.post("/v1/solana/decode-error")
async def decode_solana_error(request: SolanaDecodeRequest):
    payload_dict = {
        "signature": request.signature,
        "program_id": request.program_id,
        "accounts": request.accounts,
        "transaction": request.transaction,
        "payload": request.payload,
        "logs": request.logs,
    }

    result = decode_solana_error_payload(request.input_type, payload_dict)

    ai_requested = bool(request.use_ai)
    ai_allowed = bool(SOLANA_DECODE_USE_AI)
    ai_used = False
    ai_result = None

    if ai_requested and ai_allowed:
        ai_result = await generate_ai_decoder_explanation(result, request)
        if ai_result and ai_result.get("provider"):
            ai_used = True

    response_payload = {
        "meta": {
            "service": "AsyncSignals",
            "endpoint": "v1_solana_decode_error",
            "generated_at": utc_now_z(),
            "ai_requested": ai_requested,
            "ai_enabled": ai_requested and ai_allowed,
            "ai_used": ai_used,
            "helius_configured": bool(HELIUS_API_KEY),
            "alchemy_configured": bool(ALCHEMY_KEY),
        },
        **result,
    }

    if ai_result:
        response_payload["ai_analysis"] = ai_result

    return JSONResponse(content=to_jsonable(response_payload))

@app.get("/market")
def get_market(
    format: str = Query("json", pattern="^(json|text)$"),
    limit: int = Query(DEFAULT_MARKET_LIMIT, ge=1, le=250),
):
    items = get_cached_section("market", [])[:limit]
    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": "AsyncSignals",
            "endpoint": "market",
            "limit": limit,
            "count": len(items),
            "generated_at": meta.get("cache_loaded_at"),
            "cache_status": meta.get("cache_status"),
        },
        "items": items,
    }

    if format == "text":
        lines = ["ASYNC SIGNALS :: MARKET", ""]
        if not items:
            lines.append("No market rows found.")
        else:
            for row in items:
                lines.append(
                    f"{row.get('symbol', '-')} | price={fmt_usd(row.get('current_price'))} | "
                    f"market_cap={fmt_usd(row.get('market_cap'))} | "
                    f"24h={row.get('price_change_percentage_24h', 0)}%"
                )
        return PlainTextResponse("\n".join(lines).strip())

    return JSONResponse(content=to_jsonable(payload))


@app.get("/news")
def get_news(
    format: str = Query("json", pattern="^(json|text)$"),
    limit: int = Query(DEFAULT_NEWS_LIMIT, ge=1, le=100),
):
    items = get_cached_section("news", [])[:limit]
    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": "AsyncSignals",
            "endpoint": "news",
            "limit": limit,
            "count": len(items),
            "generated_at": meta.get("cache_loaded_at"),
            "cache_status": meta.get("cache_status"),
        },
        "items": items,
    }

    if format == "text":
        lines = ["ASYNC SIGNALS :: NEWS", ""]
        if not items:
            lines.append("No news rows found.")
        else:
            for row in items:
                lines.append(f"{row.get('pubdate', '-')} | {row.get('source_id', '-')}")
                lines.append(str(row.get("title", "")).strip())
                lines.append(str(row.get("link", "")).strip())
                lines.append("-" * 80)
        return PlainTextResponse("\n".join(lines))

    return JSONResponse(content=to_jsonable(payload))


@app.get("/whales")
def get_whales(
    format: str = Query("json", pattern="^(json|text)$"),
    limit: int = Query(DEFAULT_WHALE_LIMIT, ge=1, le=250),
    asset: Optional[str] = Query(None),
):
    items = get_cached_section("whales", [])
    if asset:
        items = filter_shared_whales_by_asset(asset)
    items = items[:limit]

    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": "AsyncSignals",
            "endpoint": "whales",
            "limit": limit,
            "asset_filter": asset.upper() if asset else None,
            "count": len(items),
            "generated_at": meta.get("cache_loaded_at"),
            "cache_status": meta.get("cache_status"),
        },
        "items": items,
    }

    if format == "text":
        return PlainTextResponse(render_shared_whales_text(items))
    return JSONResponse(content=to_jsonable(payload))


@app.get("/whales/{asset}")
def get_whales_by_asset(
    asset: str = Path(..., min_length=1),
    format: str = Query("json", pattern="^(json|text)$"),
    limit: int = Query(DEFAULT_WHALE_LIMIT, ge=1, le=250),
):
    items = filter_shared_whales_by_asset(asset)[:limit]
    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": "AsyncSignals",
            "endpoint": "whales_by_asset",
            "limit": limit,
            "asset_filter": asset.upper(),
            "count": len(items),
            "generated_at": meta.get("cache_loaded_at"),
            "cache_status": meta.get("cache_status"),
        },
        "items": items,
    }

    if format == "text":
        return PlainTextResponse(render_shared_whales_text(items))
    return JSONResponse(content=to_jsonable(payload))


@app.get("/summaries")
def get_summaries(
    format: str = Query("json", pattern="^(json|text)$"),
    asset: Optional[str] = Query(None),
):
    items = get_cached_section("summaries", [])
    if asset:
        items = filter_summaries_by_asset(asset)

    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": "AsyncSignals",
            "endpoint": "summaries",
            "asset_filter": asset.upper() if asset else None,
            "count": len(items),
            "generated_at": meta.get("cache_loaded_at"),
            "cache_status": meta.get("cache_status"),
        },
        "items": items,
    }

    return respond(payload, format, render_summaries_text)


@app.get("/summaries/{asset}")
def get_summaries_by_asset(
    asset: str = Path(..., min_length=1),
    format: str = Query("json", pattern="^(json|text)$"),
):
    items = filter_summaries_by_asset(asset)
    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": "AsyncSignals",
            "endpoint": "summaries_by_asset",
            "asset_filter": asset.upper(),
            "count": len(items),
            "generated_at": meta.get("cache_loaded_at"),
            "cache_status": meta.get("cache_status"),
        },
        "items": items,
    }

    return respond(payload, format, render_summaries_text)


@app.get("/signals")
def get_signals(
    format: str = Query("json", pattern="^(json|text)$"),
    limit: int = Query(DEFAULT_SIGNAL_LIMIT, ge=1, le=500),
    signal_type: Optional[str] = Query(None),
):
    items = get_cached_section("signals", [])
    if signal_type:
        items = filter_signals_by_type(signal_type)
    items = items[:limit]

    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": "AsyncSignals",
            "endpoint": "signals",
            "limit": limit,
            "signal_type_filter": signal_type.upper() if signal_type else None,
            "count": len(items),
            "generated_at": meta.get("cache_loaded_at"),
            "cache_status": meta.get("cache_status"),
        },
        "items": items,
    }

    return respond(payload, format, render_signals_text)


@app.get("/signals/{signal_type}")
def get_signals_by_type(
    signal_type: str = Path(..., min_length=1),
    format: str = Query("json", pattern="^(json|text)$"),
    limit: int = Query(DEFAULT_SIGNAL_LIMIT, ge=1, le=500),
):
    items = filter_signals_by_type(signal_type)[:limit]
    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": "AsyncSignals",
            "endpoint": "signals_by_type",
            "limit": limit,
            "signal_type_filter": signal_type.upper(),
            "count": len(items),
            "generated_at": meta.get("cache_loaded_at"),
            "cache_status": meta.get("cache_status"),
        },
        "items": items,
    }

    return respond(payload, format, render_signals_text)


@app.get("/polkadot")
def get_polkadot(
    format: str = Query("json", pattern="^(json|text)$"),
    derived_limit: int = Query(DEFAULT_POLKADOT_LIMIT, ge=1, le=200),
    xcm_transfer_limit: int = Query(20, ge=1, le=100),
):
    polkadot = get_cached_polkadot()
    polkadot_copy = {
        "available": polkadot.get("available", False),
        "rpc_snapshot": polkadot.get("rpc_snapshot", []),
        "chain_activity": polkadot.get("chain_activity", []),
        "derived_signals": polkadot.get("derived_signals", [])[:derived_limit],
        "extrinsic_feed": polkadot.get("extrinsic_feed", []),
        "staking": polkadot.get("staking", []),
        "treasury": polkadot.get("treasury", []),
        "validators": polkadot.get("validators", []),
        "xcm_summary": polkadot.get("xcm_summary", []),
        "xcm_transfers": polkadot.get("xcm_transfers", [])[:xcm_transfer_limit],
        "opengov": polkadot.get("opengov", []),
    }

    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": "AsyncSignals",
            "endpoint": "polkadot",
            "generated_at": meta.get("cache_loaded_at"),
            "derived_limit": derived_limit,
            "xcm_transfer_limit": xcm_transfer_limit,
            "cache_status": meta.get("cache_status"),
        },
        "items": polkadot_copy,
    }

    if format == "text":
        bundle_like = {
            "meta": payload["meta"],
            "highlights": {},
            "summaries": [],
            "signals": [],
            "market": [],
            "market_reference": [],
            "whales": [],
            "news": [],
            "polkadot": payload["items"],
        }
        return PlainTextResponse(render_bundle_text(bundle_like))

    return JSONResponse(content=to_jsonable(payload))


@app.get("/polkadot/whales")
def get_polkadot_whales(
    format: str = Query("json", pattern="^(json|text)$"),
    asset_symbol: Optional[str] = Query(None),
    min_usd: float = Query(DEFAULT_POLKADOT_WHALE_MIN_USD, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    polkadot = get_cached_polkadot()
    all_rows = polkadot.get("xcm_transfers", [])

    filtered_all = filter_polkadot_whales_from_rows(
        all_rows,
        asset_symbol=asset_symbol,
        min_usd=min_usd,
    )
    items = filtered_all[:limit]

    rows_after_asset_filter = [
        x for x in all_rows
        if not asset_symbol or str(x.get("asset_symbol", "")).upper() == asset_symbol.upper()
    ]

    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": "AsyncSignals",
            "endpoint": "polkadot_whales",
            "asset_symbol_filter": asset_symbol.upper() if asset_symbol else None,
            "min_usd": min_usd,
            "limit": limit,
            "count": len(items),
            "total_rows_before_filters": len(all_rows),
            "rows_after_asset_filter": len(rows_after_asset_filter),
            "rows_with_value_usd": count_rows_with_value_usd(rows_after_asset_filter),
            "rows_without_value_usd": count_rows_without_value_usd(rows_after_asset_filter),
            "generated_at": meta.get("cache_loaded_at"),
            "cache_status": meta.get("cache_status"),
        },
        "items": items,
    }

    if format == "text":
        return PlainTextResponse(render_polkadot_whales_text(items))
    return JSONResponse(content=to_jsonable(payload))


@app.get("/polkadot/whales/{asset_symbol}")
def get_polkadot_whales_by_asset(
    asset_symbol: str = Path(..., min_length=1),
    format: str = Query("json", pattern="^(json|text)$"),
    min_usd: float = Query(DEFAULT_POLKADOT_WHALE_MIN_USD, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    polkadot = get_cached_polkadot()
    all_rows = polkadot.get("xcm_transfers", [])

    filtered_all = filter_polkadot_whales_from_rows(
        all_rows,
        asset_symbol=asset_symbol,
        min_usd=min_usd,
    )
    items = filtered_all[:limit]

    rows_after_asset_filter = [
        x for x in all_rows
        if str(x.get("asset_symbol", "")).upper() == asset_symbol.upper()
    ]

    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": "AsyncSignals",
            "endpoint": "polkadot_whales_by_asset",
            "asset_symbol_filter": asset_symbol.upper(),
            "min_usd": min_usd,
            "limit": limit,
            "count": len(items),
            "total_rows_before_filters": len(all_rows),
            "rows_after_asset_filter": len(rows_after_asset_filter),
            "rows_with_value_usd": count_rows_with_value_usd(rows_after_asset_filter),
            "rows_without_value_usd": count_rows_without_value_usd(rows_after_asset_filter),
            "generated_at": meta.get("cache_loaded_at"),
            "cache_status": meta.get("cache_status"),
        },
        "items": items,
    }

    if format == "text":
        return PlainTextResponse(render_polkadot_whales_text(items))
    return JSONResponse(content=to_jsonable(payload))


@app.get("/bundle")
def get_bundle(format: str = Query("json", pattern="^(json|text)$")):
    payload = cached_bundle_with_meta()
    if format == "text":
        return PlainTextResponse(render_bundle_text(payload))
    return JSONResponse(content=to_jsonable(payload))




# ── Base endpoints ────────────────────────────────────────────────────────────

def fetch_base_rpc_snapshot() -> List[Dict[str, Any]]:
    if not table_exists("BASE_RPC_SNAPSHOT"):
        return []
    return run_query(
        """
        SELECT captured_at, latest_block_number, latest_block_hash, latest_block_timestamp,
               avg_block_time_seconds, tps_1min, gas_used_total, base_fee_gwei
        FROM BASE_RPC_SNAPSHOT
        ORDER BY captured_at DESC
        FETCH FIRST 1 ROWS ONLY
        """
    )


def fetch_base_chain_activity() -> List[Dict[str, Any]]:
    if not table_exists("BASE_CHAIN_ACTIVITY_DAILY"):
        return []
    return run_query(
        """
        SELECT activity_date, chain_name, tx_count, tps, total_fees_eth,
               total_fees_usd, activity_score, alert_level
        FROM BASE_CHAIN_ACTIVITY_DAILY
        ORDER BY activity_date DESC
        FETCH FIRST 1 ROWS ONLY
        """
    )


def fetch_base_ecosystem() -> List[Dict[str, Any]]:
    if not table_exists("BASE_ECOSYSTEM_DAILY"):
        return []
    return run_query(
        """
        SELECT snapshot_date, eth_price_usd, tvl_proxy, stablecoin_proxy
        FROM BASE_ECOSYSTEM_DAILY
        ORDER BY snapshot_date DESC
        FETCH FIRST 1 ROWS ONLY
        """
    )


def fetch_base_transfers(limit: int = 50) -> List[Dict[str, Any]]:
    if not table_exists("BASE_TRANSFER_SIGNALS"):
        return []
    limit = safe_limit(limit, 50, max_value=200)
    return run_query(
        f"""
        SELECT timestamp, asset_symbol, value_usd, from_address, to_address,
               tx_hash, block_number, transfer_type
        FROM BASE_TRANSFER_SIGNALS
        ORDER BY timestamp DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def fetch_base_derived(limit: int = DEFAULT_POLKADOT_LIMIT) -> List[Dict[str, Any]]:
    if not table_exists("BASE_DERIVED_SIGNALS"):
        return []
    limit = safe_limit(limit, DEFAULT_POLKADOT_LIMIT, max_value=200)
    return run_query(
        f"""
        SELECT signal_date, signal_family, signal_key, severity, score, title,
               description, metric_value_1, metric_value_2, metric_value_3, reference_id
        FROM BASE_DERIVED_SIGNALS
        ORDER BY signal_date DESC, score DESC
        FETCH FIRST {limit} ROWS ONLY
        """
    )


def build_base_bundle() -> Dict[str, Any]:
    return {
        "available": any(table_exists(t) for t in [
            "BASE_RPC_SNAPSHOT", "BASE_CHAIN_ACTIVITY_DAILY", "BASE_ECOSYSTEM_DAILY",
            "BASE_TRANSFER_SIGNALS", "BASE_DERIVED_SIGNALS"
        ]),
        "rpc_snapshot": fetch_base_rpc_snapshot(),
        "chain_activity": fetch_base_chain_activity(),
        "ecosystem": fetch_base_ecosystem(),
        "transfers": fetch_base_transfers(),
        "derived_signals": fetch_base_derived(),
    }


def render_base_text(bundle: Dict[str, Any]) -> str:
    lines = ["ASYNC SIGNALS :: BASE CHAIN", ""]
    if not bundle.get("available"):
        lines.append("Base tables not available.")
        return "".join(lines)
    rpc = bundle.get("rpc_snapshot", [])
    if rpc:
        r = rpc[0]
        lines.append(f"Block: {r.get('latest_block_number', '-')} | TPS: {r.get('tps_1min', '-')} | Gas: {r.get('gas_used_total', '-')}")
    activity = bundle.get("chain_activity", [])
    if activity:
        a = activity[0]
        lines.append(f"Activity: {a.get('tx_count', '-')} txs | Score: {a.get('activity_score', '-')} | Alert: {a.get('alert_level', '-')}")
    transfers = bundle.get("transfers", [])
    if transfers:
        total = sum(float(t.get("value_usd") or 0) for t in transfers)
        lines.append(f"Whale flow: {len(transfers)} transfers | ${total/1e6:.2f}M total")
    derived = bundle.get("derived_signals", [])
    if derived:
        lines.append(f"Derived signals: {len(derived)}")
        for d in derived[:5]:
            lines.append(f"  [{d.get('severity', '-').upper()}] {d.get('title', '-')} (score: {d.get('score', '-')})")
    return "".join(lines)


@app.get("/base")
def get_base(
    format: str = Query("json", pattern="^(json|text)$"),
    derived_limit: int = Query(DEFAULT_POLKADOT_LIMIT, ge=1, le=200),
    transfer_limit: int = Query(50, ge=1, le=200),
):
    bundle = build_base_bundle()
    bundle["derived_signals"] = bundle["derived_signals"][:derived_limit]
    bundle["transfers"] = bundle["transfers"][:transfer_limit]
    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": APP_TITLE,
            "endpoint": "base",
            "generated_at": meta.get("cache_loaded_at"),
            "derived_limit": derived_limit,
            "transfer_limit": transfer_limit,
            "cache_status": meta.get("cache_status"),
        },
        "items": bundle,
    }
    if format == "text":
        return PlainTextResponse(render_base_text(bundle))
    return JSONResponse(content=to_jsonable(payload))


@app.get("/base/whales")
def get_base_whales(
    format: str = Query("json", pattern="^(json|text)$"),
    limit: int = Query(50, ge=1, le=200),
    asset_symbol: Optional[str] = Query(None),
):
    items = fetch_base_transfers(limit=limit)
    if asset_symbol:
        items = [x for x in items if str(x.get("asset_symbol", "")).upper() == asset_symbol.upper()]
    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": APP_TITLE,
            "endpoint": "base_whales",
            "limit": limit,
            "asset_filter": asset_symbol.upper() if asset_symbol else None,
            "count": len(items),
            "generated_at": meta.get("cache_loaded_at"),
            "cache_status": meta.get("cache_status"),
        },
        "items": items,
    }
    if format == "text":
        lines = ["ASYNC SIGNALS :: BASE WHALES", ""]
        if not items:
            lines.append("No Base whale transfers found.")
        else:
            for row in items:
                lines.append(
                    f"{row.get('timestamp', '-')} | {row.get('asset_symbol', '-')} | "
                    f"usd={fmt_usd(row.get('value_usd'))} | "
                    f"{short_addr(row.get('from_address'))} -> {short_addr(row.get('to_address'))}"
                )
        return PlainTextResponse("".join(lines))
    return JSONResponse(content=to_jsonable(payload))


@app.get("/base/signals")
def get_base_signals(
    format: str = Query("json", pattern="^(json|text)$"),
    limit: int = Query(DEFAULT_POLKADOT_LIMIT, ge=1, le=200),
    signal_family: Optional[str] = Query(None),
):
    items = fetch_base_derived(limit=limit)
    if signal_family:
        items = [x for x in items if str(x.get("signal_family", "")).lower() == signal_family.lower()]
    meta = get_cache_meta()
    payload = {
        "meta": {
            "service": APP_TITLE,
            "endpoint": "base_signals",
            "limit": limit,
            "family_filter": signal_family.lower() if signal_family else None,
            "count": len(items),
            "generated_at": meta.get("cache_loaded_at"),
            "cache_status": meta.get("cache_status"),
        },
        "items": items,
    }
    if format == "text":
        lines = ["ASYNC SIGNALS :: BASE SIGNALS", ""]
        if not items:
            lines.append("No Base derived signals found.")
        else:
            for row in items:
                lines.append(
                    f"[{row.get('severity', '-').upper()}] {row.get('title', '-')} | "
                    f"score={row.get('score', '-')} | family={row.get('signal_family', '-')}"
                )
                lines.append(f"  {row.get('description', '')}")
        return PlainTextResponse("".join(lines))
    return JSONResponse(content=to_jsonable(payload))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("polkadot_api:app", host="0.0.0.0", port=8000, reload=False)